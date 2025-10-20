from fraim.core.contextuals.contextual import Contextual


class GithubStatusCheck(Contextual[str]):
    def __init__(self, content: str):
        self.content = content

    @property
    def description(self) -> str:
        return "JSON output from a Github status check"

    @description.setter
    def description(self, _: str) -> None:
        raise AttributeError("description is read-only")

    def __str__(self) -> str:
        return f"<github_status_check_output>\n{self.content}\n</github_status_check_output>"


# {
#     "action": "completed",
#     "check_run": {
#         "id": 1286253418,
#         "name": "build (18.x)",
#         "head_sha": "a4a39d2c46f2729a21b339245a46f7c025c8d0a9",
#         "status": "completed",
#         "conclusion": "success",
#         "started_at": "2025-10-16T16:20:12Z",
#         "completed_at": "2025-10-16T16:21:42Z",
#         "output": {
#             "title": "Build successful!",
#             "summary": "All build steps passed.",
#             "text": "Detailed build logs can be found here...",
#             "annotations_count": 0,
#             "annotations_url": "..."
#         },
#         "check_suite": {
#             "id": 1185332261
#         },
#         "app": {
#             "id": 1,
#             "name": "GitHub Actions"
#         }
#     },
#     "repository": {
#         "full_name": "your-org/your-repo"
#     }
# }
