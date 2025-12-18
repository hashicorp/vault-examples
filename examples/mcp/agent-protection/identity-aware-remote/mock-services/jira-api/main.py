"""
Mock Jira API Server
Simulates Jira API endpoints for demo purposes
"""
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os

app = FastAPI(title="Mock Jira API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
issues_db = {
    "PROJ-1": {
        "id": "PROJ-1",
        "key": "PROJ-1",
        "summary": "Sample Issue 1",
        "description": "This is a sample issue",
        "status": "To Do",
        "assignee": "alice",
        "project": "PROJ"
    },
    "PROJ-2": {
        "id": "PROJ-2",
        "key": "PROJ-2",
        "summary": "Sample Issue 2",
        "description": "Another sample issue",
        "status": "In Progress",
        "assignee": "bob",
        "project": "PROJ"
    }
}

projects_db = {
    "PROJ": {
        "id": "PROJ",
        "key": "PROJ",
        "name": "Sample Project",
        "description": "A sample project"
    }
}


class IssueCreate(BaseModel):
    summary: str
    description: Optional[str] = None
    project: str


class IssueUpdate(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


def verify_auth(authorization: Optional[str] = Header(None)):
    """Verify authorization header (basic auth or bearer token)"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required")
    return authorization


@app.get("/")
async def root():
    return {"message": "Mock Jira API", "version": "1.0"}


@app.get("/rest/api/3/project")
async def list_projects(authorization: Optional[str] = Header(None)):
    verify_auth(authorization)
    return list(projects_db.values())


@app.get("/rest/api/3/project/{project_key}")
async def get_project(project_key: str, authorization: Optional[str] = Header(None)):
    verify_auth(authorization)
    if project_key not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")
    return projects_db[project_key]


@app.get("/rest/api/3/search")
async def search_issues(
    jql: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    verify_auth(authorization)
    issues = list(issues_db.values())
    
    # Simple JQL parsing (for demo)
    if jql:
        if "assignee" in jql:
            assignee = jql.split("assignee=")[1].split()[0].strip('"')
            issues = [i for i in issues if i.get("assignee") == assignee]
    
    return {
        "startAt": 0,
        "maxResults": len(issues),
        "total": len(issues),
        "issues": issues
    }


@app.get("/rest/api/3/issue/{issue_key}")
async def get_issue(issue_key: str, authorization: Optional[str] = Header(None)):
    verify_auth(authorization)
    
    # If issue_key exists in database, return it
    if issue_key in issues_db:
        return issues_db[issue_key]
    
    # If issue_key is a project name (exists in projects_db), return first issue of that project
    if issue_key in projects_db:
        project_issues = [issue for issue in issues_db.values() if issue.get("project") == issue_key]
        if project_issues:
            # Return the first issue of the project
            return project_issues[0]
        else:
            # Return project info if no issues exist
            return {
                "id": issue_key,
                "key": issue_key,
                "summary": f"Project: {projects_db[issue_key]['name']}",
                "description": f"No issues found in project {issue_key}. Available issues: {', '.join(issues_db.keys())}",
                "status": "Project",
                "assignee": None,
                "project": issue_key,
                "note": "This is a project name, not an issue key. Use format PROJ-1, PROJ-2, etc."
            }
    
    # If not found, return a helpful error message
    available_issues = list(issues_db.keys())
    available_projects = list(projects_db.keys())
    raise HTTPException(
        status_code=404, 
        detail=f"Issue '{issue_key}' not found. Available issues: {', '.join(available_issues)}. Available projects: {', '.join(available_projects)}"
    )


@app.post("/rest/api/3/issue")
async def create_issue(issue: IssueCreate, authorization: Optional[str] = Header(None)):
    verify_auth(authorization)
    if issue.project not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")
    
    new_key = f"{issue.project}-{len(issues_db) + 1}"
    new_issue = {
        "id": new_key,
        "key": new_key,
        "summary": issue.summary,
        "description": issue.description or "",
        "status": "To Do",
        "assignee": None,
        "project": issue.project
    }
    issues_db[new_key] = new_issue
    return new_issue


@app.put("/rest/api/3/issue/{issue_key}")
async def update_issue(
    issue_key: str,
    issue: IssueUpdate,
    authorization: Optional[str] = Header(None)
):
    verify_auth(authorization)
    if issue_key not in issues_db:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    if issue.summary:
        issues_db[issue_key]["summary"] = issue.summary
    if issue.description is not None:
        issues_db[issue_key]["description"] = issue.description
    if issue.status:
        issues_db[issue_key]["status"] = issue.status
    
    return issues_db[issue_key]


@app.delete("/rest/api/3/issue/{issue_key}")
async def delete_issue(issue_key: str, authorization: Optional[str] = Header(None)):
    verify_auth(authorization)
    if issue_key not in issues_db:
        raise HTTPException(status_code=404, detail="Issue not found")
    del issues_db[issue_key]
    return {"message": "Issue deleted"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

