from fraim.core.contextuals.contextual import Contextual, Locations


class GithubStatusCheck(Contextual[str]):
    def __init__(self, content: str):
        self.content = content

    @property
    def description(self) -> str:
        return "JSON output from a Github status check"

    @description.setter
    def description(self, _: str) -> None:
        raise AttributeError("description is read-only")

    @property
    def locations(self) -> Locations:
        return Locations()

    def __str__(self) -> str:
        return f"<github_status_check_output>\n{self.content}\n</github_status_check_output>"
