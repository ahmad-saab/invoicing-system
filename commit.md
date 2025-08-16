# Project Version Commit Instructions

This file instructs the model to create versioned snapshots of the project, similar to git commits but as complete folder copies.

## How to Use This File

When you want to create a new version of the project, ask the model to:
1. Read this `commit.md` file
2. Follow the instructions below to create a new version

## Version Creation Instructions for Model

### Step 1: Determine Next Version Number
- Look for existing version folders in the current directory (e.g., `invoice_system_version_1`, `invoice_system_version_2`)
- Determine the next version number
- If no versions exist, start with `version_1`

### Step 2: Create New Version Folder
- Create folder named: `invoice_system_version_X` (where X is the next version number)
- Copy **ALL** project files to this new folder, including:
  - All Python files (*.py)
  - Database file (test_customers.db)
  - Frontend folder with all contents
  - Configuration files (requirements.txt, etc.)
  - Documentation files (README.md, Isys.md)
  - All other project files and subdirectories

**IMPORTANT**: Copy everything except:
- `venv/` folder (virtual environment)
- `__pycache__/` folders
- `.git/` folder (if exists)
- Temporary files and logs (*.log, temp/ contents)
- `node_modules/` folder (can be recreated with npm install)

### Step 3: Create Version Documentation
Create a file called `VERSION_CHANGES.md` inside the new version folder with:

```markdown
# Version X Changes - [Date]

## Summary
[Brief description of what changed in this version]

## Files Modified
- [List of files that were changed]

## New Features
- [List of new features added]

## Bug Fixes
- [List of bugs fixed]

## Technical Changes
- [Database schema changes]
- [API endpoint changes]
- [Frontend component changes]
- [Other technical modifications]

## Dependencies
- [Any new dependencies added]
- [Dependencies removed or updated]

## Testing Notes
- [Notes about testing this version]
- [Known issues if any]

## Rollback Instructions
If this version has issues:
1. Stop all services
2. Copy files from previous version folder
3. Restart services
```

### Step 4: Update Project History
Update the main `Isys.md` file by adding a new section at the top:

```markdown
## Version X Release ([Date])

### Changes Made
[Detailed description of changes]

### Version Location
Files saved in: `invoice_system_version_X/`

### Stability Status
- [ ] Development
- [ ] Testing  
- [x] Stable (mark when confirmed stable)

---

[Previous content remains below]
```

### Step 5: Confirmation
After creating the version:
1. Verify all important files were copied
2. Create a summary of what was versioned
3. Provide the user with:
   - Version number created
   - Location of version folder
   - Summary of changes
   - Instructions to test the new version

## Example Usage

**User says**: "Please commit the current project as version 2 with the customer pricing system we just implemented"

**Model should**:
1. Create `invoice_system_version_2/` folder
2. Copy all project files to this folder
3. Create `VERSION_CHANGES.md` with customer pricing implementation details
4. Update `Isys.md` with version 2 information
5. Report back what was done

## File Structure After Versioning

```
invoice.atrade.ae/
├── commit.md (this file)
├── [current project files]
├── invoice_system_version_1/
│   ├── VERSION_CHANGES.md
│   ├── [all project files as of version 1]
│   └── [complete working copy]
├── invoice_system_version_2/
│   ├── VERSION_CHANGES.md  
│   ├── [all project files as of version 2]
│   └── [complete working copy]
└── Isys.md (updated with all version history)
```

## Important Notes for Model

1. **Always copy ALL files** - don't risk missing important changes
2. **Each version folder should be self-contained** and runnable
3. **Never delete old versions** unless explicitly asked
4. **Update Isys.md** to maintain complete project history
5. **Include clear change descriptions** in VERSION_CHANGES.md
6. **Preserve file permissions** and structure when copying

## Version Stability Marking

Versions can be marked as:
- **Development**: Work in progress, may have issues
- **Testing**: Ready for testing, not production
- **Stable**: Confirmed working, safe for production use

Only mark as stable after user confirmation that the version works properly.