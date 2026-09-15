import json
from pathlib import Path
import numpy as np
import joblib
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix, classification_report, brier_score_loss
)
from sklearn.model_selection import GroupKFold, StratifiedKFold
from sklearn.preprocessing import StandardScaler, label_binarize
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV

from app.services.ml.classifier_pipeline import ThermalClassifierPipeline, CLASSES, FEATURE_NAMES

pipeline = ThermalClassifierPipeline()
X, y, groups, metadata = pipeline.generate_audited_dataset(n_samples=2480, seed=42)

print("============================================================")
print("1. DATASET COMPOSITION & PROVENANCE")
print("============================================================")
print(f"Total Samples: {len(X)}")
print(f"Features: {len(FEATURE_NAMES)}")
print(f"Unique Groups/Facilities: {len(set(groups))}")

unique, counts = np.unique(y, return_counts=True)
class_counts = dict(zip(unique, counts))
print("Class Distribution:")
for k, v in class_counts.items():
    print(f"  {k:24s}: {v:4d} ({v/len(y)*100:.1f}%)")

# Grouped split: 60% Train, 20% Val, 20% Test
gkf = GroupKFold(n_splits=5)
train_idx, test_idx = next(gkf.split(X, y, groups=groups))

X_train_full, y_train_full = X[train_idx], y[train_idx]
groups_train = [groups[i] for i in train_idx]
X_test, y_test = X[test_idx], y[test_idx]

gkf_inner = GroupKFold(n_splits=4)
train_sub_idx, val_idx = next(gkf_inner.split(X_train_full, y_train_full, groups=groups_train))

X_train, y_train = X_train_full[train_sub_idx], y_train_full[train_sub_idx]
X_val, y_val = X_train_full[val_idx], y_train_full[val_idx]

print(f"\nGroup Split (No Facility Leakage):")
print(f"  Train: {len(X_train)} samples ({len(set(groups[i] for i in train_idx[train_sub_idx]))} groups)")
print(f"  Val:   {len(X_val)} samples ({len(set(groups[i] for i in train_idx[val_idx]))} groups)")
print(f"  Test:  {len(X_test)} samples ({len(set(groups[i] for i in test_idx))} groups)")

print("\n============================================================")
print("2. MODEL COMPARISON (HIST_GRAD_BOOST VS RANDOM_FOREST VS LOGISTIC_REGRESSION)")
print("============================================================")
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

models = {
    "HistGradientBoosting": HistGradientBoostingClassifier(max_iter=150, learning_rate=0.08, max_depth=6, min_samples_leaf=15, class_weight="balanced", random_state=42),
    "RandomForest": RandomForestClassifier(n_estimators=120, max_depth=12, min_samples_split=6, class_weight="balanced", random_state=42, n_jobs=-1),
    "LogisticRegression": LogisticRegression(max_iter=500, class_weight="balanced", random_state=42)
}

comparison = {}
for name, clf in models.items():
    X_tr = X_train_s if name == "LogisticRegression" else X_train
    X_te = X_test_s if name == "LogisticRegression" else X_test
    
    clf.fit(X_tr, y_train)
    preds = clf.predict(X_te)
    probs = clf.predict_proba(X_te)
    
    acc = accuracy_score(y_test, preds)
    bal_acc = balanced_accuracy_score(y_test, preds)
    macro_f1 = f1_score(y_test, preds, average="macro")
    weighted_f1 = f1_score(y_test, preds, average="weighted")
    ind_recall = recall_score(y_test == "INDUSTRIAL_FIRE", preds == "INDUSTRIAL_FIRE")
    
    # FPR and FNR for industrial fire
    ind_true = (y_test == "INDUSTRIAL_FIRE")
    ind_pred = (preds == "INDUSTRIAL_FIRE")
    fn = np.sum(ind_true & (~ind_pred))
    tp = np.sum(ind_true & ind_pred)
    fp = np.sum((~ind_true) & ind_pred)
    tn = np.sum((~ind_true) & (~ind_pred))
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    
    comparison[name] = {
        "Accuracy": acc,
        "Balanced_Accuracy": bal_acc,
        "Macro_F1": macro_f1,
        "Weighted_F1": weighted_f1,
        "Ind_Fire_Recall": ind_recall,
        "Ind_Fire_FPR": fpr,
        "Ind_Fire_FNR": fnr
    }
    print(f"Model: {name:20s} | Acc: {acc:.4f} | BalAcc: {bal_acc:.4f} | MacroF1: {macro_f1:.4f} | IndRecall: {ind_recall:.4f} | FPR: {fpr:.4f}")

print("\n============================================================")
print("3. CALIBRATED HIST GRADIENT BOOSTING EVALUATION")
print("============================================================")
cal_model = CalibratedClassifierCV(
    estimator=HistGradientBoostingClassifier(max_iter=150, learning_rate=0.08, max_depth=6, min_samples_leaf=15, class_weight="balanced", random_state=42),
    method="sigmoid",
    cv=3
)
cal_model.fit(X_train_full, y_train_full)
test_preds = cal_model.predict(X_test)
test_probs = cal_model.predict_proba(X_test)

acc = accuracy_score(y_test, test_preds)
bal_acc = balanced_accuracy_score(y_test, test_preds)
macro_f1 = f1_score(y_test, test_preds, average="macro")
weighted_f1 = f1_score(y_test, test_preds, average="weighted")

print(f"Calibrated Model Overall Accuracy: {acc:.4f}")
print(f"Balanced Accuracy:                {bal_acc:.4f}")
print(f"Macro F1:                         {macro_f1:.4f}")
print(f"Weighted F1:                      {weighted_f1:.4f}")

# Multi-class Brier score
y_test_bin = label_binarize(y_test, classes=cal_model.classes_)
brier = np.mean(np.sum((test_probs - y_test_bin) ** 2, axis=1))
print(f"Multi-class Brier Score:          {brier:.4f}")

print("\nClassification Report:")
print(classification_report(y_test, test_preds, digits=4))

cm = confusion_matrix(y_test, test_preds, labels=cal_model.classes_)
print("Confusion Matrix:")
print("Classes:", list(cal_model.classes_))
print(cm)

print("\n============================================================")
print("4. FEATURE ABLATION STUDY")
print("============================================================")
# Feature groupings:
# A: FIRMS-only (frp_current, temp_current, day_night_ratio, night_fraction) -> [0, 6, 18, 19]
# B: FIRMS + Facility (A + facility_distance_m, is_inside_facility, dispersion_radius_r95) -> [0, 6, 18, 19, 11, 12, 13]
# C: + Land Cover Context (B + sta_overlap) -> [0, 6, 18, 19, 11, 12, 13, 21]
# D: + Persistence / Fingerprint (C + frp_median, robust_z, temp_median, temp_dep, active_days, obs_count, recurrence_rate, detection_rate)
# E: + Multi-satellite (D + satellite_count)
# F: All Features (Full 23 features)

ablation_configs = {
    "A: FIRMS-Only (Thermal Current Only)": [0, 6, 18, 19],
    "B: FIRMS + Facility Proximity & Dispersion": [0, 6, 18, 19, 11, 12, 13],
    "C: + Land Cover / Spatial Overlap": [0, 6, 18, 19, 11, 12, 13, 21],
    "D: + Persistence & Baseline Fingerprint": [0, 1, 2, 4, 6, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 21],
    "E: + Multi-Satellite Sensor Agreement": [0, 1, 2, 4, 6, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22],
    "F: Complete Multi-Tier Feature Set (Full 23)": list(range(23))
}

ablation_results = {}
for name, f_indices in ablation_configs.items():
    X_tr_abl = X_train[:, f_indices]
    X_te_abl = X_test[:, f_indices]
    
    clf_abl = HistGradientBoostingClassifier(max_iter=150, learning_rate=0.08, max_depth=6, min_samples_leaf=15, class_weight="balanced", random_state=42)
    clf_abl.fit(X_tr_abl, y_train)
    preds_abl = clf_abl.predict(X_te_abl)
    
    acc_a = accuracy_score(y_test, preds_abl)
    f1_a = f1_score(y_test, preds_abl, average="macro")
    ind_rec_a = recall_score(y_test == "INDUSTRIAL_FIRE", preds_abl == "INDUSTRIAL_FIRE")
    
    ind_true = (y_test == "INDUSTRIAL_FIRE")
    ind_pred = (preds_abl == "INDUSTRIAL_FIRE")
    fp_a = int(np.sum((~ind_true) & ind_pred))
    fn_a = int(np.sum(ind_true & (~ind_pred)))
    
    ablation_results[name] = {
        "Accuracy": acc_a,
        "Macro_F1": f1_a,
        "Industrial_Fire_Recall": ind_rec_a,
        "Industrial_Fire_FP": fp_a,
        "Industrial_Fire_FN": fn_a,
        "Feature_Count": len(f_indices)
    }
    print(f"{name:45s} | Feats: {len(f_indices):2d} | Macro F1: {f1_a:.4f} | Ind Recall: {ind_rec_a:.4f} | Ind FP: {fp_a:2d} | Ind FN: {fn_a:2d}")

print("\n============================================================")
print("5. SAVED MODEL ARTIFACT INTEGRITY CHECK")
print("============================================================")
model_path = Path(__file__).resolve().parent / "app" / "models" / "thermal_classifier_v1.joblib"
meta_path = Path(__file__).resolve().parent / "app" / "models" / "thermal_classifier_metadata.json"
saved = joblib.load(model_path)
with open(meta_path) as f:
    saved_meta = json.load(f)

print("Saved model classes:", saved.get("classes"))
print("Metadata model name:", saved_meta.get("model_name"))
print("Metadata primary model:", saved_meta.get("primary_model_type"))
print("Metadata reported Macro F1:", saved_meta.get("macro_f1"))
print("Metadata reported Industrial Fire Recall:", saved_meta.get("industrial_fire_recall"))
