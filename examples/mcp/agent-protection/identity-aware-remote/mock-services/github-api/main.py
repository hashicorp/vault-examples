"""
Mock Github API Server
Simulates Github API endpoints for demo purposes
"""
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os

app = FastAPI(title="Mock Github API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
repos_db = {
    "repo1": {
        "id": 1,
        "name": "repo1",
        "full_name": "user/repo1",
        "description": "Sample repository 1",
        "private": False,
        "owner": {
            "login": "user",
            "id": 1
        },
        "stargazers_count": 10,
        "forks_count": 5
    },
    "repo2": {
        "id": 2,
        "name": "repo2",
        "full_name": "user/repo2",
        "description": "Sample repository 2",
        "private": True,
        "owner": {
            "login": "user",
            "id": 1
        },
        "stargazers_count": 20,
        "forks_count": 8
    }
}

issues_db = {
    1: {
        "id": 1,
        "number": 1,
        "title": "Sample Issue 1",
        "body": "This is a sample issue",
        "state": "open",
        "user": {
            "login": "alice"
        },
        "repository": "repo1"
    },
    2: {
        "id": 2,
        "number": 2,
        "title": "Sample Issue 2",
        "body": "Another sample issue",
        "state": "closed",
        "user": {
            "login": "bob"
        },
        "repository": "repo1"
    }
}


class RepoCreate(BaseModel):
    name: str
    description: Optional[str] = None
    private: bool = False


class IssueCreate(BaseModel):
    title: str
    body: Optional[str] = None


def verify_auth(authorization: Optional[str] = Header(None)):
    """Verify authorization header (bearer token)"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required")
    if not authorization.startswith("Bearer ") and not authorization.startswith("token "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    return authorization


@app.get("/")
async def root():
    return {"message": "Mock Github API", "version": "1.0"}


@app.get("/user/repos")
async def list_user_repos(authorization: Optional[str] = Header(None)):
    verify_auth(authorization)
    return list(repos_db.values())


@app.get("/repos/{owner}/{repo}")
async def get_repo(owner: str, repo: str, authorization: Optional[str] = Header(None)):
    verify_auth(authorization)
    if repo not in repos_db:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repos_db[repo]


@app.post("/user/repos")
async def create_repo(repo: RepoCreate, authorization: Optional[str] = Header(None)):
    verify_auth(authorization)
    if repo.name in repos_db:
        raise HTTPException(status_code=422, detail="Repository already exists")
    
    new_repo = {
        "id": len(repos_db) + 1,
        "name": repo.name,
        "full_name": f"user/{repo.name}",
        "description": repo.description or "",
        "private": repo.private,
        "owner": {
            "login": "user",
            "id": 1
        },
        "stargazers_count": 0,
        "forks_count": 0
    }
    repos_db[repo.name] = new_repo
    return new_repo


@app.get("/repos/{owner}/{repo}/issues")
async def list_repo_issues(
    owner: str,
    repo: str,
    state: Optional[str] = "open",
    authorization: Optional[str] = Header(None)
):
    verify_auth(authorization)
    if repo not in repos_db:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    issues = [i for i in issues_db.values() if i["repository"] == repo]
    if state:
        issues = [i for i in issues if i["state"] == state]
    
    return issues


@app.get("/repos/{owner}/{repo}/issues/{issue_number}")
async def get_issue(
    owner: str,
    repo: str,
    issue_number: int,
    authorization: Optional[str] = Header(None)
):
    verify_auth(authorization)
    if issue_number not in issues_db:
        raise HTTPException(status_code=404, detail="Issue not found")
    if issues_db[issue_number]["repository"] != repo:
        raise HTTPException(status_code=404, detail="Issue not found in this repository")
    return issues_db[issue_number]


@app.post("/repos/{owner}/{repo}/issues")
async def create_issue(
    owner: str,
    repo: str,
    issue: IssueCreate,
    authorization: Optional[str] = Header(None)
):
    verify_auth(authorization)
    if repo not in repos_db:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    new_id = max(issues_db.keys(), default=0) + 1
    new_issue = {
        "id": new_id,
        "number": new_id,
        "title": issue.title,
        "body": issue.body or "",
        "state": "open",
        "user": {
            "login": "user"
        },
        "repository": repo
    }
    issues_db[new_id] = new_issue
    return new_issue


@app.patch("/repos/{owner}/{repo}/issues/{issue_number}")
async def update_issue(
    owner: str,
    repo: str,
    issue_number: int,
    issue: IssueCreate,
    authorization: Optional[str] = Header(None)
):
    verify_auth(authorization)
    if issue_number not in issues_db:
        raise HTTPException(status_code=404, detail="Issue not found")
    if issues_db[issue_number]["repository"] != repo:
        raise HTTPException(status_code=404, detail="Issue not found in this repository")
    
    issues_db[issue_number]["title"] = issue.title
    if issue.body is not None:
        issues_db[issue_number]["body"] = issue.body
    
    return issues_db[issue_number]


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

