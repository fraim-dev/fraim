import logging
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests  # type: ignore[import-untyped]

from .models import CodeChange


logger = logging.getLogger(__name__)


class GitCodeExtractor:
    """Extracts vulnerable and fixed code from Git repositories."""

    def __init__(self, temp_dir: Optional[Path] = None):
        self.temp_dir = temp_dir or Path(tempfile.mkdtemp())
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.cloned_repos: Dict[str, Path] = {}

    def extract_code_changes_from_references(self, references: List[str], cve_id: str) -> List[CodeChange]:
        code_changes: List[CodeChange] = []
        for ref in references:
            try:
                changes = self._extract_from_reference(ref, cve_id)
                code_changes.extend(changes)
                
                if len(code_changes) > 0:
                    logger.info(f"Extracted code changes from {ref}")
                    break
            except Exception as e:
                logger.debug(f"Failed to extract code from {ref}: {e}")
                continue
        return code_changes

    def _extract_from_reference(self, reference: str, cve_id: str) -> List[CodeChange]:
        parsed_url = urlparse(reference)
        if parsed_url.netloc == 'github.com' and '/commit/' in reference:
            return self._extract_from_github_commit(reference, cve_id)
        # elif parsed_url.netloc == 'github.com' and '/pull/' in reference:
        #     return self._extract_from_github_pr(reference, cve_id)
        # elif reference.endswith('.patch') or '.patch' in reference:
        #     return self._extract_from_patch_url(reference, cve_id)
        return []

    def _extract_from_github_commit(self, commit_url: str, cve_id: str) -> List[CodeChange]:
        try:
            parts = commit_url.split('/')
            if len(parts) < 7:
                return []
            owner, repo = parts[3], parts[4]
            # Strip any query/hash fragments to get a clean commit hash
            commit_hash = parts[6].split('?')[0].split('#')[0]
            repo_key = f"{owner}/{repo}"
            repo_path = self._ensure_repo_cloned(f"https://github.com/{repo_key}.git", repo_key)
            if not repo_path:
                return []
            return [self._get_changed_files_content(repo_path, commit_hash, commit_url)]
        except Exception as e:
            logger.error(f"Error extracting from GitHub commit {commit_url}: {e}")
            return []

    def _ensure_repo_cloned(self, repo_url: str, repo_key: str) -> Optional[Path]:
        if repo_key in self.cloned_repos:
            return self.cloned_repos[repo_key]
        try:
            repo_path = self.temp_dir / repo_key.replace('/', '_')
            if repo_path.exists():
                if (repo_path / '.git').exists():
                    self.cloned_repos[repo_key] = repo_path
                    return repo_path
                else:
                    suffix = str(int(time.time()))
                    repo_path = self.temp_dir / f"{repo_key.replace('/', '_')}_{suffix}"
            logger.info(f"Cloning repository: {repo_url} to {repo_path}")
            result = subprocess.run(
                ['git', 'clone', '--depth', '1000', repo_url, str(repo_path)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                self.cloned_repos[repo_key] = repo_path
                return repo_path
            else:
                if 'already exists and is not an empty directory' in (result.stderr or '') and (self.temp_dir / repo_key.replace('/', '_')).exists():
                    existing_path = self.temp_dir / repo_key.replace('/', '_')
                    if (existing_path / '.git').exists():
                        self.cloned_repos[repo_key] = existing_path
                        logger.warning(f"Using existing clone at {existing_path} for {repo_url}")
                        return existing_path
                logger.error(f"Failed to clone {repo_url}: {result.stderr}")
                return None
        except subprocess.TimeoutExpired:
            logger.error(f"Timed out cloning repository {repo_url}")
            return None
        except Exception as e:
            logger.error(f"Error cloning repository {repo_url}: {e}")
            return None
        
    def _list_changed_paths(self, repo_path: Path, commit: str) -> List[Tuple[str, str, str]]:
        """
        Returns a list of tuples: (status, old_path, new_path)
        """
        try:
            out = subprocess.run(
                ["git", "diff-tree", "-r", "--no-commit-id", "--name-status", "-M", commit],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"Timed out listing changed paths for commit {commit} in {repo_path}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing changed paths for commit {commit} in {repo_path}: {e}")
            return []

        if out.returncode != 0:
            stderr = (out.stderr or '').strip()
            logger.warning(f"git diff-tree failed for commit {commit} in {repo_path}: {stderr}")
            return []

        changes: List[Tuple[str, str, str]] = []
        for line in out.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            status = parts[0]
            if status.startswith("R") and len(parts) >= 3:
                old_path, new_path = parts[1], parts[2]
            elif status.startswith("D") and len(parts) >= 2:
                old_path = parts[1]
                new_path = old_path
            elif len(parts) >= 2:
                old_path = parts[1]
                new_path = parts[1]
            else:
                logger.debug(f"Unrecognized diff-tree line for commit {commit}: {line}")
                continue
            changes.append((status, old_path, new_path))
        return changes

    def _git_show_blob(self, repo_path: Path, rev: str, path: str) -> str:
        """Return file content (string) for <rev>:<path>, or '' if not found."""
        cmd = ["git", "show", f"{rev}:{path}"]
        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"Timed out showing blob for {rev}:{path} in {repo_path}")
            return ""
        except Exception as e:
            logger.debug(f"Unexpected error showing blob for {rev}:{path} in {repo_path}: {e}")
            return ""

        if result.returncode != 0:
            # Likely file does not exist in this revision; not an error
            return ""

        try:
            return result.stdout
        except Exception:
            # Fallback for potential decode issues; attempt binary read and skip binaries
            try:
                result_bin = subprocess.run(
                    cmd,
                    cwd=repo_path,
                    capture_output=True,
                    text=False,
                    timeout=30,
                )
                if result_bin.returncode != 0:
                    return ""
                content_bytes = result_bin.stdout or b""
                if b"\x00" in content_bytes:
                    # Likely binary; skip
                    logger.debug(f"Skipping binary file content for {rev}:{path}")
                    return ""
                return content_bytes.decode("utf-8", errors="replace")
            except Exception:
                return ""

    def _get_changed_files_content(self, repo_path: Path, commit: str, commit_url: str) -> CodeChange:
        """
        Returns two strings:
            old_code_str: concatenation of all changed files from parent commit
            new_code_str: concatenation of all changed files from target commit
        """
        try:
            parent = f"{commit}^1"
            changes = self._list_changed_paths(repo_path, commit)

            if not changes:
                logger.warning(f"No changed paths found for commit {commit} in {repo_path}")

            old_code_pieces: List[str] = []
            new_code_pieces: List[str] = []

            for _, old_path, new_path in changes:
                old_content = self._git_show_blob(repo_path, parent, old_path)
                new_content = self._git_show_blob(repo_path, commit, new_path)

                if old_content:
                    old_code_pieces.append(f"--- {old_path} ---\n{old_content}")
                if new_content:
                    new_code_pieces.append(f"+++ {new_path} +++\n{new_content}")

            old_code_str = "\n".join(old_code_pieces)
            new_code_str = "\n".join(new_code_pieces)
            
            return CodeChange(
                vulnerable_code=old_code_str,
                fixed_code=new_code_str,
                commit_hash=commit,
                repo_url=commit_url,
            )
        except Exception as e:
            logger.error(f"Error assembling changed files content for commit {commit} in {repo_path}: {e}")
            raise e

    def _get_language_from_path(self, file_path: str) -> str:
        ext_to_lang = {
            '.py': 'python',
            '.java': 'java',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.php': 'php',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.go': 'go',
            '.rb': 'ruby',
            '.rs': 'rust',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.sh': 'bash',
            '.pl': 'perl',
            '.r': 'r',
            '.sql': 'sql',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.json': 'json',
        }
        for ext, lang in ext_to_lang.items():
            if file_path.endswith(ext):
                return lang
        return 'text'

    def cleanup(self) -> None:
        try:
            import shutil
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory: {e}")


