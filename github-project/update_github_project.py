#!/usr/bin/env python3
"""
Script to automatically create GitHub project items from a JSON task list.
Uses GitHub CLI (gh) to interact with GitHub Projects.
"""

import json
import subprocess
import sys
from typing import Dict, List, Any

def load_tasks(json_file: str) -> List[Dict[str, Any]]:
    """Load tasks from JSON file."""
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File {json_file} not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {json_file}: {e}")
        sys.exit(1)

def get_project_info() -> tuple[str, str]:
    """Get the GitHub project number and owner for the current repository."""
    try:
        # Get repository info
        result = subprocess.run(
            ["gh", "repo", "view", "--json", "owner"],
            capture_output=True,
            text=True,
            check=True
        )
        repo_info = json.loads(result.stdout)
        owner = repo_info["owner"]["login"]
        
        # List projects for this owner
        result = subprocess.run(
            ["gh", "project", "list", "--owner", owner],
            capture_output=True,
            text=True,
            check=True
        )
        
        if not result.stdout.strip():
            print("No GitHub projects found. Please create a project first:")
            print("gh project create --title 'Trade Alert System'")
            sys.exit(1)
            
        # Parse project list - no header to skip, just get the first line
        lines = result.stdout.strip().split('\n')
        if lines and lines[0]:
            project_number = lines[0].split('\t')[0]
            return project_number, owner
        else:
            print("No projects found")
            sys.exit(1)
            
    except subprocess.CalledProcessError as e:
        print(f"Error getting project info: {e}")
        print("Make sure you have GitHub CLI installed and are authenticated")
        sys.exit(1)

def map_status_to_github(status: str) -> str:
    """Map task status to GitHub project status."""
    status_mapping = {
        "To Do": "Todo",
        "In Progress": "In Progress", 
        "Done": "Done",
        "Backlog": "Backlog"
    }
    return status_mapping.get(status, "Todo")

def create_project_item(project_number: str, owner: str, title: str, body: str) -> bool:
    """Create a project item using GitHub CLI."""
    try:
        # Extract status from body
        status = body.replace("Status: ", "").strip()
        github_status = map_status_to_github(status)
        
        # Create the project item
        cmd = [
            "gh", "project", "item-create", project_number,
            "--owner", owner,
            "--title", title,
            "--body", f"Status: {status}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # gh project item-create succeeds silently, so if no exception was raised, it worked
        print(f"✓ Created: {title}")
        
        # Note: Status field updates are complex and require project-specific field IDs
        # For now, we'll just create the items with the status in the body
        # Users can manually update statuses in the GitHub UI if needed
        
        return True
            
    except subprocess.CalledProcessError as e:
        print(f"✗ Error creating {title}: {e}")
        if e.stderr:
            print(f"  Details: {e.stderr}")
        return False

def main():
    """Main function to process tasks and create project items."""
    json_file = "github_project_tasks.json"
    
    print("Loading tasks from JSON file...")
    tasks = load_tasks(json_file)
    
    print("Getting GitHub project information...")
    project_number, owner = get_project_info()
    print(f"Using project: {project_number} (owner: {owner})")
    
    print(f"\nCreating {len(tasks)} project items...")
    success_count = 0
    
    for task in tasks:
        title = task.get("title", "")
        body = task.get("body", "")
        
        if not title:
            print("⚠ Skipping task with empty title")
            continue
            
        if create_project_item(project_number, owner, title, body):
            success_count += 1
    
    print(f"\n✅ Successfully created {success_count}/{len(tasks)} project items")
    
    if success_count < len(tasks):
        print("\n⚠ Some items failed to create. Common issues:")
        print("  - Project permissions")
        print("  - GitHub CLI authentication")
        print("  - Duplicate items (if items already exist)")

if __name__ == "__main__":
    main()