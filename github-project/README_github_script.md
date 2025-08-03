# GitHub Project Updater

This script automatically creates GitHub project items from the tasks defined in `github_project_tasks.json`.

## Prerequisites

1. **GitHub CLI installed**: Install from https://cli.github.com/
2. **GitHub CLI authenticated**: Run `gh auth login`
3. **GitHub Project exists**: Create one if needed with `gh project create --title "Trade Alert System"`

## Usage

```bash
# Run the script
python3 update_github_project.py

# Or make it executable and run directly
chmod +x update_github_project.py
./update_github_project.py
```

## What the script does

1. Reads tasks from `github_project_tasks.json`
2. Finds your GitHub project for this repository
3. Creates project items with titles and status from the JSON
4. Maps status values:
   - "To Do" → "Todo"
   - "In Progress" → "In Progress"
   - "Done" → "Done"
   - "Backlog" → "Backlog"

## JSON Format

The script expects this format in `github_project_tasks.json`:

```json
[
  {
    "title": "Task title",
    "body": "Status: To Do"
  }
]
```

## Troubleshooting

- **No projects found**: Create a project first with `gh project create`
- **Permission denied**: Check GitHub CLI authentication with `gh auth status`
- **Duplicate items**: The script doesn't check for existing items - run only once or clean up duplicates manually

## Notes

- Status field updates might require additional project configuration
- The script creates items but doesn't handle updates to existing items
- Run this script once when setting up your project board