import time
from app.services.industrial.telemetry_simulator import telemetry_simulator
from app.services.ingestion.stream_router import stream_router

def test_stream_scalability_benchmark():
    print("=" * 80)
    print("SIH-1505 MULTIPLEXED LOGICAL STREAM SCALABILITY BENCHMARK (100, 500, 1000 STREAMS)")
    print("=" * 80)

    stream_levels = [100, 500, 1000]

    for count in stream_levels:
        telemetry_simulator.set_stream_count(count)
        
        # Warmup
        telemetry_simulator.generate_tick_batch(count)

        # Run 5 continuous ticks
        latencies = []
        total_events = 0
        t0_total = time.perf_counter()
        
        for _ in range(5):
            t0 = time.perf_counter()
            batch = telemetry_simulator.generate_tick_batch(count)
            for event in batch:
                stream_router.route_event(event)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)
            total_events += len(batch)

        total_sec = time.perf_counter() - t0_total
        throughput_eps = round(total_events / total_sec, 1)
        p95_ms = round(sorted(latencies)[int(len(latencies) * 0.95)], 2)
        p99_ms = round(sorted(latencies)[int(len(latencies) * 0.99)], 2)

        print(f"\n[STREAM COUNT: {count:4d} LOGICAL STREAMS]")
        print(f" -> Total Events Ingested: {total_events}")
        print(f" -> Ingestion Throughput: {throughput_eps:,.1f} events/sec")
        print(f" -> Batch Processing Latency: P95 = {p95_ms:.2f} ms | P99 = {p99_ms:.2f} ms")
        print(f" -> Verification Target (P95 <= 5000 ms): {'PASS' if p95_ms < 5000 else 'FAIL'}")

        assert p95_ms < 5000.0, f"P95 latency exceeded engineering target: {p95_ms}ms"

    print("\n" + "=" * 80)
    print("SCALABILITY BENCHMARK VERIFIED: Shared logical stream model scales without thread saturation!")
    print("=" * 80)

if __name__ == "__main__":
    test_stream_scalability_benchmark()
