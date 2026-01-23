#!/usr/bin/env bash
#
# sync.sh - Documentation synchronization script
#
# Synchronizes README.md, CHANGELOG.md, and API docs with implementation.
# Preserves user content outside speckit markers.
#

set -euo pipefail

# ============================================================================
# EMBEDDED UTILITIES - DO NOT EDIT (regenerate with scripts/build.sh)
# ============================================================================

# --- path-resolver.sh ---
#
# path-resolver.sh - Shared path resolution utilities for speckit-gates skills
#
# Usage:
#   source path-resolver.sh
#   resolve_paths  # Sets FEATURE_DIR, SPEC_FILE, PLAN_FILE, etc.
#


# Colors for output (using COLOR_* naming convention)
readonly COLOR_RED='\033[0;31m'
readonly COLOR_YELLOW='\033[1;33m'
readonly COLOR_GREEN='\033[0;32m'
readonly COLOR_NC='\033[0m' # No Color

# Find the repository root by looking for .git or .specify
find_repo_root() {
    local dir="$PWD"
    while [[ "$dir" != "/" ]]; do
        if [[ -d "$dir/.git" ]] || [[ -d "$dir/.specify" ]]; then
            echo "$dir"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    return 1
}

# Resolve all paths using check-prerequisites.sh
resolve_paths() {
    local repo_root
    repo_root="$(find_repo_root)" || {
        echo -e "${COLOR_RED}Error: Could not find repository root${COLOR_NC}" >&2
        return 1
    }

    local prereq_script="$repo_root/.specify/scripts/bash/check-prerequisites.sh"

    if [[ ! -f "$prereq_script" ]]; then
        echo -e "${COLOR_RED}Error: check-prerequisites.sh not found at $prereq_script${COLOR_NC}" >&2
        return 1
    fi

    # Run check-prerequisites.sh --json and parse output
    local json_output
    json_output=$("$prereq_script" --json 2>/dev/null) || {
        echo -e "${COLOR_RED}Error: Failed to run check-prerequisites.sh${COLOR_NC}" >&2
        return 1
    }

    # Extract FEATURE_DIR from JSON
    FEATURE_DIR=$(echo "$json_output" | grep -o '"FEATURE_DIR":"[^"]*"' | cut -d'"' -f4)

    if [[ -z "$FEATURE_DIR" ]]; then
        echo -e "${COLOR_RED}Error: Could not determine FEATURE_DIR${COLOR_NC}" >&2
        return 1
    fi

    # Set standard paths
    REPO_ROOT="$repo_root"
    SPEC_FILE="$FEATURE_DIR/spec.md"
    PLAN_FILE="$FEATURE_DIR/plan.md"
    TASKS_FILE="$FEATURE_DIR/tasks.md"
    DATA_MODEL_FILE="$FEATURE_DIR/data-model.md"
    RESEARCH_FILE="$FEATURE_DIR/research.md"
    QUICKSTART_FILE="$FEATURE_DIR/quickstart.md"
    CONTRACTS_DIR="$FEATURE_DIR/contracts"
    CONSTITUTION_FILE="$repo_root/constitution.md"

    # Export for subshells
    export REPO_ROOT FEATURE_DIR SPEC_FILE PLAN_FILE TASKS_FILE
    export DATA_MODEL_FILE RESEARCH_FILE QUICKSTART_FILE CONTRACTS_DIR
    export CONSTITUTION_FILE

    return 0
}

# Check if a required file exists
require_file() {
    local file="$1"
    local name="${2:-$file}"

    if [[ ! -f "$file" ]]; then
        echo -e "${COLOR_RED}Error: Required file missing: $name${COLOR_NC}" >&2
        echo "Path: $file" >&2
        return 1
    fi
    return 0
}

# Check if an optional file exists (returns success either way)
check_optional_file() {
    local file="$1"
    [[ -f "$file" ]]
}

# Get the feature branch name from FEATURE_DIR
get_feature_branch() {
    if [[ -n "${FEATURE_DIR:-}" ]]; then
        basename "$FEATURE_DIR"
    else
        echo "unknown"
    fi
}

# Get current timestamp in ISO 8601 format
get_timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# --- output-format.sh ---
#
# output-format.sh - Shared output formatting utilities for speckit-gates skills
#
# Usage:
#   source output-format.sh
#   print_status GREEN "All checks passed"
#

# Colors for terminal output
readonly COLOR_BLUE='\033[0;34m'
readonly COLOR_GRAY='\033[0;90m'
readonly COLOR_BOLD='\033[1m'

# Status emoji
readonly STATUS_GREEN="GREEN"
readonly STATUS_YELLOW="YELLOW"
readonly STATUS_RED="RED"

# Print a header section
print_header() {
    local skill_name="$1"
    local feature_branch="$2"
    local status="$3"
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    local status_display
    case "$status" in
        GREEN)  status_display="GREEN" ;;
        YELLOW) status_display="YELLOW" ;;
        RED)    status_display="RED" ;;
        *)      status_display="$status" ;;
    esac

    echo "## Quality Assessment: $skill_name"
    echo ""
    echo "**Status**: $status_display"
    echo "**Branch**: $feature_branch"
    echo "**Timestamp**: $timestamp"
    echo ""
}

# Print a section title
print_section() {
    local title="$1"
    echo "### $title"
    echo ""
}

# Print a finding entry
print_finding() {
    local severity="$1"
    local artifact="$2"
    local message="$3"

    local severity_display
    case "$severity" in
        error)   severity_display="error" ;;
        warning) severity_display="warning" ;;
        info)    severity_display="info" ;;
        *)       severity_display="$severity" ;;
    esac

    echo "| $severity_display | $artifact | $message |"
}

# Print findings table header
print_findings_header() {
    echo "| Severity | Artifact | Message |"
    echo "|----------|----------|---------|"
}

# Print a blocker entry
print_blocker() {
    local id="$1"
    local description="$2"
    local action="$3"

    echo "- **$id**: $description"
    echo "  - Suggested action: $action"
}

# Print a recommendation
print_recommendation() {
    local message="$1"
    echo "- $message"
}

# Print a check item (for release-check)
print_check_item() {
    local status="$1"
    local name="$2"
    local details="${3:-}"

    local icon
    case "$status" in
        pass) icon="[PASS]" ;;
        fail) icon="[FAIL]" ;;
        skip) icon="[SKIP]" ;;
        *)    icon="[ ? ]" ;;
    esac

    if [[ -n "$details" ]]; then
        echo "| $icon | $name | $details |"
    else
        echo "| $icon | $name | |"
    fi
}

# Print check items table header
print_check_table_header() {
    echo "| Status | Check | Details |"
    echo "|--------|-------|---------|"
}

# Print a progress bar (for progress-report)
print_progress_bar() {
    local completed="$1"
    local total="$2"
    local width="${3:-20}"

    if [[ "$total" -eq 0 ]]; then
        echo "[--------------------] 0%"
        return
    fi

    local percentage=$((completed * 100 / total))
    local filled=$((completed * width / total))
    local empty=$((width - filled))

    local bar=""
    for ((i=0; i<filled; i++)); do bar+="#"; done
    for ((i=0; i<empty; i++)); do bar+="-"; done

    echo "[$bar] $percentage% ($completed/$total)"
}

# Print a summary line
print_summary() {
    local label="$1"
    local value="$2"
    echo "**$label**: $value"
}

# Print coverage metrics
print_coverage() {
    local label="$1"
    local implemented="$2"
    local total="$3"

    if [[ "$total" -eq 0 ]]; then
        echo "- **$label**: N/A (no items)"
        return
    fi

    local percentage=$((implemented * 100 / total))
    echo "- **$label**: $implemented/$total ($percentage%)"
}

# Print a table row
print_table_row() {
    local columns=("$@")
    local row="|"
    for col in "${columns[@]}"; do
        row+=" $col |"
    done
    echo "$row"
}

# Print an error message to stderr
print_error() {
    local message="$1"
    echo -e "${COLOR_RED}Error: $message${COLOR_NC}" >&2
}

# Print a warning message to stderr
print_warning() {
    local message="$1"
    echo -e "${COLOR_YELLOW}Warning: $message${COLOR_NC}" >&2
}

# Print an info message
print_info() {
    local message="$1"
    echo -e "${COLOR_BLUE}Info: $message${COLOR_NC}"
}

# --- error-handler.sh ---
#
# error-handler.sh - Shared error handling utilities for speckit-gates skills
#
# Exit Codes:
#   0 - Success (GREEN status for validation skills)
#   1 - Warnings present (YELLOW status) or partial success
#   2 - Errors present (RED status) or low fulfillment
#   3 - Fatal error (missing required files, unexpected errors)
#

# Exit codes as constants
readonly EXIT_SUCCESS=0
readonly EXIT_WARNING=1
readonly EXIT_ERROR=2
readonly EXIT_FATAL=3

# Global error tracking
declare -g ERROR_COUNT=0
declare -g WARNING_COUNT=0
declare -g ERRORS=()
declare -g WARNINGS=()

# Reset error state
reset_errors() {
    ERROR_COUNT=0
    WARNING_COUNT=0
    ERRORS=()
    WARNINGS=()
}

# Record an error
record_error() {
    local message="$1"
    ERRORS+=("$message")
    ((ERROR_COUNT++)) || true
}

# Record a warning
record_warning() {
    local message="$1"
    WARNINGS+=("$message")
    ((WARNING_COUNT++)) || true
}

# Get error count
get_error_count() {
    echo "$ERROR_COUNT"
}

# Get warning count
get_warning_count() {
    echo "$WARNING_COUNT"
}

# Determine exit code based on error/warning counts
determine_exit_code() {
    if [[ "$ERROR_COUNT" -gt 0 ]]; then
        echo "$EXIT_ERROR"
    elif [[ "$WARNING_COUNT" -gt 0 ]]; then
        echo "$EXIT_WARNING"
    else
        echo "$EXIT_SUCCESS"
    fi
}

# Determine status based on error/warning counts
determine_status() {
    if [[ "$ERROR_COUNT" -gt 0 ]]; then
        echo "RED"
    elif [[ "$WARNING_COUNT" -gt 0 ]]; then
        echo "YELLOW"
    else
        echo "GREEN"
    fi
}

# Exit with error for missing required file
exit_missing_file() {
    local file="$1"
    local name="${2:-$file}"

    echo ""
    echo "## Error: Required File Missing"
    echo ""
    echo "**File**: $name"
    echo "**Path**: $file"
    echo ""
    echo "### Suggested Actions"
    echo ""
    echo "1. Ensure you have run the prerequisite spec kit commands"
    echo "2. Check that you are in the correct feature directory"
    echo "3. Verify the file exists at the expected path"
    echo ""

    exit "$EXIT_FATAL"
}

# Exit with error for unexpected error
exit_unexpected_error() {
    local message="$1"
    local details="${2:-}"

    echo ""
    echo "## Error: Unexpected Error"
    echo ""
    echo "**Message**: $message"
    if [[ -n "$details" ]]; then
        echo "**Details**: $details"
    fi
    echo ""
    echo "### Suggested Actions"
    echo ""
    echo "1. Check the error message for hints"
    echo "2. Verify your environment is correctly configured"
    echo "3. Report the issue if the problem persists"
    echo ""

    exit "$EXIT_FATAL"
}

# Print all recorded errors
print_errors() {
    if [[ "${#ERRORS[@]}" -eq 0 ]]; then
        return
    fi

    echo "### Errors"
    echo ""
    for error in "${ERRORS[@]}"; do
        echo "- $error"
    done
    echo ""
}

# Print all recorded warnings
print_warnings() {
    if [[ "${#WARNINGS[@]}" -eq 0 ]]; then
        return
    fi

    echo "### Warnings"
    echo ""
    for warning in "${WARNINGS[@]}"; do
        echo "- $warning"
    done
    echo ""
}

# Trap handler for unexpected script termination
handle_exit() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]] && [[ $exit_code -ne "$EXIT_WARNING" ]] && [[ $exit_code -ne "$EXIT_ERROR" ]]; then
        echo ""
        echo "## Skill Terminated Unexpectedly"
        echo ""
        echo "Exit code: $exit_code"
        echo ""
    fi
}

# Set up exit trap
setup_error_trap() {
    trap handle_exit EXIT
}

# Validate that a command exists
require_command() {
    local cmd="$1"
    if ! command -v "$cmd" &> /dev/null; then
        exit_unexpected_error "Required command not found: $cmd" "Please install $cmd and try again."
    fi
}

# ============================================================================
# END EMBEDDED UTILITIES
# ============================================================================




# Initialize
reset_errors
setup_error_trap

# Results storage
declare -i FILES_CREATED=0
declare -i FILES_UPDATED=0
declare -i FILES_UNCHANGED=0
declare -i FILES_ERROR=0
declare -i LINES_ADDED=0
declare -i LINES_REMOVED=0

declare -a UPDATES=()
declare -a ERRORS_LIST=()

# Add an update record
add_update() {
    local file="$1"
    local status="$2"
    local sections="$3"
    UPDATES+=("$file|$status|$sections")
}

# Add an error record
add_error() {
    local file="$1"
    local message="$2"
    ERRORS_LIST+=("$file: $message")
}

# Extract feature summary from spec.md
get_feature_summary() {
    if [[ ! -f "$SPEC_FILE" ]]; then
        echo "Feature documentation"
        return
    fi

    local content
    content=$(cat "$SPEC_FILE")

    # Try to find summary section content
    local summary
    summary=$(echo "$content" | sed -n '/^##\s*Summary/,/^##/p' | head -10 | tail -n +2 | grep -v '^##' || true)

    if [[ -n "$summary" ]]; then
        echo "$summary" | head -3
    else
        # Fall back to first paragraph after title
        echo "$content" | sed -n '1,/^$/p' | tail -n +2 | head -3
    fi
}

# Extract completed tasks from tasks.md
get_completed_tasks() {
    if [[ ! -f "$TASKS_FILE" ]]; then
        return
    fi

    local content
    content=$(cat "$TASKS_FILE")

    # Get completed tasks
    echo "$content" | grep -E '^\s*-\s*\[[Xx]\]' | sed 's/^\s*-\s*\[[Xx]\]\s*/- /' | head -20
}

# Update a section in a file using markers (FR-020)
update_section() {
    local file="$1"
    local section="$2"
    local content="$3"

    local start_marker="<!-- speckit:start:$section -->"
    local end_marker="<!-- speckit:end:$section -->"

    if [[ ! -f "$file" ]]; then
        # File doesn't exist, create with markers
        {
            echo "$start_marker"
            echo "$content"
            echo "$end_marker"
        } > "$file"
        return 0
    fi

    local file_content
    file_content=$(cat "$file")

    if echo "$file_content" | grep -qF "$start_marker"; then
        # Markers exist, replace content between them
        local temp_file
        temp_file=$(mktemp)

        local in_section=0
        while IFS= read -r line || [[ -n "$line" ]]; do
            if [[ "$line" == *"$start_marker"* ]]; then
                echo "$line"
                echo "$content"
                in_section=1
            elif [[ "$line" == *"$end_marker"* ]]; then
                echo "$line"
                in_section=0
            elif [[ "$in_section" -eq 0 ]]; then
                echo "$line"
            fi
        done < "$file" > "$temp_file"

        mv "$temp_file" "$file"
    else
        # No markers, append at end
        {
            echo ""
            echo "$start_marker"
            echo "$content"
            echo "$end_marker"
        } >> "$file"
    fi

    return 0
}

# Update README.md usage section (FR-017)
update_readme() {
    local readme_file="$REPO_ROOT/README.md"

    if [[ ! -f "$readme_file" ]]; then
        add_update "README.md" "skipped" "file not found"
        return
    fi

    local original_lines
    original_lines=$(wc -l < "$readme_file")

    # Generate usage content from spec
    local usage_content=""
    if [[ -f "$SPEC_FILE" ]]; then
        local feature_branch
        feature_branch=$(get_feature_branch)
        usage_content="## Usage

This section is auto-generated from spec kit artifacts.

See the [specification](./specs/$feature_branch/spec.md) for detailed requirements."
    fi

    if [[ -n "$usage_content" ]]; then
        if update_section "$readme_file" "usage" "$usage_content"; then
            local new_lines
            new_lines=$(wc -l < "$readme_file")
            local diff=$((new_lines - original_lines))
            if [[ "$diff" -gt 0 ]]; then
                ((LINES_ADDED += diff)) || true
            elif [[ "$diff" -lt 0 ]]; then
                ((LINES_REMOVED += (-diff))) || true
            fi

            if [[ "$diff" -ne 0 ]]; then
                ((FILES_UPDATED++)) || true
                add_update "README.md" "updated" "usage"
            else
                ((FILES_UNCHANGED++)) || true
                add_update "README.md" "unchanged" ""
            fi
        else
            ((FILES_ERROR++)) || true
            add_error "README.md" "Failed to update usage section"
        fi
    else
        ((FILES_UNCHANGED++)) || true
        add_update "README.md" "unchanged" "no content to sync"
    fi
}

# Update CHANGELOG.md (FR-018)
update_changelog() {
    local changelog_file="$REPO_ROOT/CHANGELOG.md"

    if [[ ! -f "$changelog_file" ]]; then
        add_update "CHANGELOG.md" "skipped" "file not found"
        return
    fi

    local original_lines
    original_lines=$(wc -l < "$changelog_file")

    # Generate unreleased content from completed tasks
    local completed_tasks
    completed_tasks=$(get_completed_tasks)

    if [[ -n "$completed_tasks" ]]; then
        local unreleased_content="### Added

$completed_tasks"

        if update_section "$changelog_file" "unreleased" "$unreleased_content"; then
            local new_lines
            new_lines=$(wc -l < "$changelog_file")
            local diff=$((new_lines - original_lines))
            if [[ "$diff" -gt 0 ]]; then
                ((LINES_ADDED += diff)) || true
            elif [[ "$diff" -lt 0 ]]; then
                ((LINES_REMOVED += (-diff))) || true
            fi

            if [[ "$diff" -ne 0 ]]; then
                ((FILES_UPDATED++)) || true
                add_update "CHANGELOG.md" "updated" "unreleased"
            else
                ((FILES_UNCHANGED++)) || true
                add_update "CHANGELOG.md" "unchanged" ""
            fi
        else
            ((FILES_ERROR++)) || true
            add_error "CHANGELOG.md" "Failed to update unreleased section"
        fi
    else
        ((FILES_UNCHANGED++)) || true
        add_update "CHANGELOG.md" "unchanged" "no completed tasks"
    fi
}

# Update API documentation (FR-019)
update_api_docs() {
    if [[ ! -d "$CONTRACTS_DIR" ]]; then
        return
    fi

    local api_docs_file="$REPO_ROOT/docs/api.md"

    # Check if docs directory exists
    if [[ ! -d "$REPO_ROOT/docs" ]]; then
        return
    fi

    if [[ ! -f "$api_docs_file" ]]; then
        return
    fi

    local original_lines
    original_lines=$(wc -l < "$api_docs_file")

    # Generate API content from contracts
    local api_content="## API Reference

Auto-generated from contract specifications.

See [contracts/](./specs/$(get_feature_branch)/contracts/) for detailed API contracts."

    if update_section "$api_docs_file" "api" "$api_content"; then
        local new_lines
        new_lines=$(wc -l < "$api_docs_file")
        local diff=$((new_lines - original_lines))
        if [[ "$diff" -gt 0 ]]; then
            ((LINES_ADDED += diff)) || true
        elif [[ "$diff" -lt 0 ]]; then
            ((LINES_REMOVED += (-diff))) || true
        fi

        if [[ "$diff" -ne 0 ]]; then
            ((FILES_UPDATED++)) || true
            add_update "docs/api.md" "updated" "api"
        else
            ((FILES_UNCHANGED++)) || true
            add_update "docs/api.md" "unchanged" ""
        fi
    else
        ((FILES_ERROR++)) || true
        add_error "docs/api.md" "Failed to update api section"
    fi
}

# Output results (FR-021)
output_results() {
    local feature_branch
    feature_branch=$(get_feature_branch)
    local timestamp
    timestamp=$(get_timestamp)

    echo "## DocsSyncResult: docs-sync"
    echo ""
    echo "**Branch**: $feature_branch"
    echo "**Timestamp**: $timestamp"
    echo ""

    # Summary
    print_section "Summary"
    echo "- Files created: $FILES_CREATED"
    echo "- Files updated: $FILES_UPDATED"
    echo "- Files unchanged: $FILES_UNCHANGED"
    echo "- Errors: $FILES_ERROR"
    echo ""

    # Diff summary
    if [[ "$LINES_ADDED" -gt 0 ]] || [[ "$LINES_REMOVED" -gt 0 ]]; then
        print_section "Diff Summary"
        echo "- Lines added: $LINES_ADDED"
        echo "- Lines removed: $LINES_REMOVED"
        echo ""
    fi

    # Updates
    if [[ "${#UPDATES[@]}" -gt 0 ]]; then
        print_section "File Updates"
        echo "| File | Status | Sections Modified |"
        echo "|------|--------|-------------------|"
        for update in "${UPDATES[@]}"; do
            IFS='|' read -r file status sections <<< "$update"
            echo "| $file | $status | $sections |"
        done
        echo ""
    fi

    # Errors
    if [[ "${#ERRORS_LIST[@]}" -gt 0 ]]; then
        print_section "Errors"
        for error in "${ERRORS_LIST[@]}"; do
            echo "- $error"
        done
        echo ""
    fi
}

# Main execution
main() {
    # Resolve paths
    if ! resolve_paths; then
        exit_unexpected_error "Failed to resolve paths" "Ensure you are in a spec kit project"
    fi

    # Check for required files (FR-038)
    # docs-sync can work with partial files, so we just warn

    # Run all sync operations
    update_readme
    update_changelog
    update_api_docs

    # Output results
    output_results

    # Determine exit code
    if [[ "$FILES_ERROR" -gt 0 ]]; then
        exit 1
    else
        exit 0
    fi
}

main "$@"
