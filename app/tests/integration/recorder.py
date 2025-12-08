from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class APITestRecorder:
    base_url: str
    start_time: datetime = field(default_factory=datetime.now)
    test_results: List[Dict[str, Any]] = field(default_factory=list)
    performance_stats: Dict[str, List[float]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def record(
        self,
        *,
        test_name: str,
        method: str,
        endpoint: str,
        url: str,
        status_code: Optional[int],
        expected_status: Optional[int],
        expected_statuses: Optional[Iterable[int]],
        success: bool,
        response_time: float,
        params: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        request_id: Optional[str] = None,
        response_preview: Optional[str] = None,
        response_body: Optional[str] = None,
        response_is_json: bool = False,
    ) -> None:
        entry = {
            "test_name": test_name,
            "method": method,
            "endpoint": endpoint,
            "url": url,
            "status_code": status_code,
            "expected_status": expected_status,
            "expected_statuses": list(expected_statuses) if expected_statuses else None,
            "success": success,
            "response_time": round(response_time, 3),
            "params": dict(params) if params else None,
            "error": error,
            "request_id": request_id,
            "response_preview": response_preview,
            "response_body": response_body,
            "response_is_json": response_is_json,
            "timestamp": datetime.now().isoformat(),
        }
        self.test_results.append(entry)
        self.performance_stats[f"{method} {endpoint}"].append(response_time)

    def generate_performance_report(self) -> str:
        if not self.performance_stats:
            return "No performance data available.\n"

        endpoint_stats = []
        for endpoint, times in self.performance_stats.items():
            if not times:
                continue
            avg_time = sum(times) / len(times)
            endpoint_stats.append(
                {
                    "endpoint": endpoint,
                    "count": len(times),
                    "avg": round(avg_time, 3),
                    "min": round(min(times), 3),
                    "max": round(max(times), 3),
                }
            )

        endpoint_stats.sort(key=lambda item: item["avg"], reverse=True)

        slow_endpoints = [item for item in endpoint_stats if item["avg"] > 1.0]
        very_slow_endpoints = [item for item in endpoint_stats if item["avg"] > 5.0]

        lines = [
            f"Total unique endpoints tested: {len(endpoint_stats)}",
            f"Slow endpoints (>1s average): {len(slow_endpoints)}",
            f"Very slow endpoints (>5s average): {len(very_slow_endpoints)}",
            "",
        ]

        if slow_endpoints:
            lines.append("SLOW ENDPOINTS (>1s average response time):")
            lines.append("-" * 80)
            for stat in slow_endpoints[:10]:
                lines.append(
                    f"{stat['endpoint']}: {stat['avg']}s avg "
                    f"(min {stat['min']}s / max {stat['max']}s over {stat['count']} calls)"
                )
            lines.append("")

        lines.append("ALL ENDPOINT PERFORMANCE (sorted by average response time):")
        lines.append("-" * 80)
        for stat in endpoint_stats[:20]:
            lines.append(
                f"{stat['endpoint']}: {stat['avg']}s avg "
                f"(min {stat['min']}s / max {stat['max']}s over {stat['count']} calls)"
            )

        return "\n".join(lines) + "\n"

    def generate_report(self) -> str:
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result.get("success"))
        failed_tests = total_tests - passed_tests

        success_rate = (passed_tests / total_tests * 100) if total_tests else 0

        lines = [
            "=" * 80,
            "API TEST REPORT - Contact360 Backend",
            "=" * 80,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Base URL: {self.base_url}",
            "",
            "SUMMARY",
            "=" * 80,
            f"Total Tests: {total_tests}",
            f"Passed: {passed_tests}",
            f"Failed: {failed_tests}",
            f"Success Rate: {success_rate:.1f}%",
            "",
            "PERFORMANCE",
            "=" * 80,
            self.generate_performance_report(),
            "=" * 80,
            "DETAILED RESULTS",
            "=" * 80,
        ]

        for idx, result in enumerate(self.test_results, start=1):
            status = "PASS" if result.get("success") else "FAIL"
            lines.extend(
                [
                    "",
                    f"{idx}. {status} - {result.get('test_name', 'Unknown Test')}",
                    f"   Method: {result.get('method')}",
                    f"   URL: {result.get('url')}",
                    f"   Status Code: {result.get('status_code')} "
                    f"(Expected: {result.get('expected_status') or result.get('expected_statuses')})",
                    f"   Response Time: {result.get('response_time')}s",
                ]
            )
            params = result.get("params")
            if params:
                lines.append(f"   Parameters: {params}")
            if result.get("error"):
                lines.append(f"   Error: {result['error']}")
            if result.get("request_id"):
                lines.append(f"   Request ID: {result['request_id']}")
            preview = result.get("response_preview")
            if preview:
                lines.append(f"   Response Preview: {preview}")

        lines.append("\n" + "=" * 80)
        return "\n".join(lines)

    def _output_directory(self, pytestconfig) -> Path:
        root_path = Path(pytestconfig.rootpath)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = root_path / "@results" / timestamp
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _sanitize_name(self, value: str) -> str:
        safe = "".join(ch if ch.isalnum() or ch in "-._" else "_" for ch in value)
        return safe.strip("._") or "response"

    def _write_response_files(self, output_dir: Path) -> List[Path]:
        written_files: List[Path] = []
        for index, result in enumerate(self.test_results, start=1):
            body = result.get("response_body")
            if body is None:
                continue
            slug_base = self._sanitize_name(result.get("test_name", f"test_{index}"))
            extension = ".json" if result.get("response_is_json") else ".txt"
            target = output_dir / f"{index:04d}_{slug_base}{extension}"
            if result.get("response_is_json"):
                try:
                    parsed = json.loads(body)
                except (TypeError, ValueError):
                    target = target.with_suffix(".txt")
                    target.write_text(body, encoding="utf-8")
                else:
                    target.write_text(json.dumps(parsed, indent=2, default=str), encoding="utf-8")
            else:
                target.write_text(body, encoding="utf-8")
            written_files.append(target)
        return written_files

    def write_outputs(self, pytestconfig) -> Dict[str, Path]:
        """Persist report, JSON summary, and raw responses to disk."""
        report_text = self.generate_report()
        output_dir = self._output_directory(pytestconfig)

        report_path = output_dir / "api_test_report.txt"
        report_path.write_text(report_text, encoding="utf-8")

        json_path = output_dir / "api_test_results.json"
        json_payload = {
            "summary": {
                "total_tests": len(self.test_results),
                "passed_tests": sum(1 for r in self.test_results if r.get("success")),
                "failed_tests": sum(1 for r in self.test_results if not r.get("success")),
                "base_url": self.base_url,
                "generated_at": datetime.now().isoformat(),
            },
            "performance_stats": {
                endpoint: {
                    "count": len(times),
                    "avg": round(sum(times) / len(times), 3) if times else 0,
                    "min": round(min(times), 3) if times else 0,
                    "max": round(max(times), 3) if times else 0,
                }
                for endpoint, times in self.performance_stats.items()
            },
            "test_results": self.test_results,
        }
        json_path.write_text(json.dumps(json_payload, indent=2, default=str), encoding="utf-8")

        responses_dir = output_dir / "responses"
        responses_dir.mkdir(exist_ok=True)
        response_files = self._write_response_files(responses_dir)

        return {
            "report": report_path,
            "json": json_path,
            "responses_dir": responses_dir,
            "response_file_count": len(response_files),
        }

