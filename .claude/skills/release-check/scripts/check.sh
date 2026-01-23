#!/usr/bin/env bash
#
# check.sh - Release readiness check script
#
# Validates all artifacts are complete and consistent for release.
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

# Check results storage
declare -a ARTIFACT_CHECKS=()
declare -a DOC_CHECKS=()
declare -a VERSION_CHECKS=()
declare -a API_CHECKS=()

declare -i PASS_COUNT=0
declare -i FAIL_COUNT=0
declare -i SKIP_COUNT=0

# Version info
PACKAGE_VERSION=""
CHANGELOG_VERSION=""
VERSIONS_CONSISTENT=true

# Add a check result
add_check() {
    local category="$1"
    local status="$2"
    local name="$3"
    local details="${4:-}"

    case "$status" in
        pass) ((PASS_COUNT++)) || true ;;
        fail) ((FAIL_COUNT++)) || true ;;
        skip) ((SKIP_COUNT++)) || true ;;
    esac

    local entry="$status|$name|$details"
    case "$category" in
        artifacts) ARTIFACT_CHECKS+=("$entry") ;;
        documentation) DOC_CHECKS+=("$entry") ;;
        versioning) VERSION_CHECKS+=("$entry") ;;
        api) API_CHECKS+=("$entry") ;;
    esac
}

# Check spec kit artifacts (FR-022)
check_artifacts() {
    # spec.md
    if [[ -f "$SPEC_FILE" ]]; then
        add_check "artifacts" "pass" "spec.md exists"
    else
        add_check "artifacts" "fail" "spec.md exists" "File not found"
    fi

    # plan.md
    if [[ -f "$PLAN_FILE" ]]; then
        add_check "artifacts" "pass" "plan.md exists"
    else
        add_check "artifacts" "fail" "plan.md exists" "File not found"
    fi

    # tasks.md
    if [[ -f "$TASKS_FILE" ]]; then
        add_check "artifacts" "pass" "tasks.md exists"

        # Check if all tasks are complete
        local total_tasks completed_tasks
        total_tasks=$(grep -cE '^\s*-\s*\[[Xx ]\]' "$TASKS_FILE" || echo "0")
        completed_tasks=$(grep -cE '^\s*-\s*\[[Xx]\]' "$TASKS_FILE" || echo "0")

        if [[ "$total_tasks" -eq "$completed_tasks" ]]; then
            add_check "artifacts" "pass" "All tasks complete" "$completed_tasks/$total_tasks"
        else
            local remaining=$((total_tasks - completed_tasks))
            add_check "artifacts" "fail" "All tasks complete" "$remaining tasks remaining"
        fi
    else
        add_check "artifacts" "fail" "tasks.md exists" "File not found"
    fi
}

# Check README.md sections (FR-023)
check_readme() {
    local readme_file="$REPO_ROOT/README.md"

    if [[ ! -f "$readme_file" ]]; then
        add_check "documentation" "fail" "README.md exists" "File not found"
        return
    fi

    add_check "documentation" "pass" "README.md exists"

    local content
    content=$(cat "$readme_file")

    # Check for usage section
    if echo "$content" | grep -qiE '^##?\s*(Usage|Quick Start|Getting Started)'; then
        add_check "documentation" "pass" "README.md has usage section"
    else
        add_check "documentation" "fail" "README.md has usage section" "No Usage section found"
    fi

    # Check for installation section
    if echo "$content" | grep -qiE '^##?\s*Installation'; then
        add_check "documentation" "pass" "README.md has installation section"
    else
        add_check "documentation" "skip" "README.md has installation section" "Optional"
    fi
}

# Check CHANGELOG.md (FR-024)
check_changelog() {
    local changelog_file="$REPO_ROOT/CHANGELOG.md"

    if [[ ! -f "$changelog_file" ]]; then
        add_check "documentation" "fail" "CHANGELOG.md exists" "File not found"
        return
    fi

    add_check "documentation" "pass" "CHANGELOG.md exists"

    local content
    content=$(cat "$changelog_file")

    # Check for unreleased section
    if echo "$content" | grep -qiE '^\[?Unreleased\]?'; then
        add_check "documentation" "pass" "CHANGELOG.md has Unreleased section"
    else
        add_check "documentation" "skip" "CHANGELOG.md has Unreleased section" "May be released"
    fi

    # Extract latest version from CHANGELOG
    CHANGELOG_VERSION=$(echo "$content" | grep -oE '^\[?[0-9]+\.[0-9]+\.[0-9]+' | head -1 | tr -d '[]' || true)
}

# Check version consistency (FR-026)
check_versions() {
    local package_file="$REPO_ROOT/package.json"

    # Get package.json version if exists
    if [[ -f "$package_file" ]]; then
        PACKAGE_VERSION=$(grep -oE '"version"\s*:\s*"[0-9]+\.[0-9]+\.[0-9]+"' "$package_file" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || true)
        if [[ -n "$PACKAGE_VERSION" ]]; then
            add_check "versioning" "pass" "package.json version" "$PACKAGE_VERSION"
        else
            add_check "versioning" "skip" "package.json version" "No version field"
        fi
    else
        add_check "versioning" "skip" "package.json exists" "Not a Node.js project"
    fi

    # Check CHANGELOG version
    if [[ -n "$CHANGELOG_VERSION" ]]; then
        add_check "versioning" "pass" "CHANGELOG.md version" "$CHANGELOG_VERSION"
    else
        add_check "versioning" "skip" "CHANGELOG.md version" "No version found"
    fi

    # Check consistency
    if [[ -n "$PACKAGE_VERSION" ]] && [[ -n "$CHANGELOG_VERSION" ]]; then
        if [[ "$PACKAGE_VERSION" == "$CHANGELOG_VERSION" ]]; then
            add_check "versioning" "pass" "Version consistency" "Both $PACKAGE_VERSION"
            VERSIONS_CONSISTENT=true
        else
            add_check "versioning" "fail" "Version consistency" "package.json: $PACKAGE_VERSION, CHANGELOG: $CHANGELOG_VERSION"
            VERSIONS_CONSISTENT=false
        fi
    else
        add_check "versioning" "skip" "Version consistency" "Not enough versions to compare"
    fi
}

# Check API documentation (FR-025)
check_api_docs() {
    if [[ ! -d "$CONTRACTS_DIR" ]]; then
        add_check "api" "skip" "API contracts" "No contracts/ directory"
        return
    fi

    local contract_count
    contract_count=$(find "$CONTRACTS_DIR" -name "*.md" -type f 2>/dev/null | wc -l)

    if [[ "$contract_count" -eq 0 ]]; then
        add_check "api" "skip" "API contracts" "No contract files"
        return
    fi

    add_check "api" "pass" "API contracts exist" "$contract_count file(s)"

    # Check for API documentation
    local api_docs_file="$REPO_ROOT/docs/api.md"
    if [[ -f "$api_docs_file" ]]; then
        add_check "api" "pass" "API documentation exists"
    else
        add_check "api" "skip" "API documentation" "docs/api.md not found"
    fi
}

# Print check category
print_check_category() {
    local title="$1"
    shift
    local checks=("$@")

    if [[ "${#checks[@]}" -eq 0 ]]; then
        return
    fi

    echo "### $title"
    echo ""
    print_check_table_header

    for check in "${checks[@]}"; do
        IFS='|' read -r status name details <<< "$check"
        print_check_item "$status" "$name" "$details"
    done
    echo ""
}

# Output checklist (FR-027)
output_checklist() {
    local feature_branch
    feature_branch=$(get_feature_branch)
    local timestamp
    timestamp=$(get_timestamp)

    local is_ready="Not Ready"
    if [[ "$FAIL_COUNT" -eq 0 ]]; then
        is_ready="Ready to Release"
    fi

    echo "## Release Checklist: release-check"
    echo ""
    echo "**Status**: $is_ready"
    echo "**Branch**: $feature_branch"
    echo "**Timestamp**: $timestamp"
    echo ""

    # Summary
    print_section "Summary"
    echo "- Passed: $PASS_COUNT"
    echo "- Failed: $FAIL_COUNT"
    echo "- Skipped: $SKIP_COUNT"
    echo ""

    # Print check categories
    print_check_category "Artifacts" "${ARTIFACT_CHECKS[@]}"
    print_check_category "Documentation" "${DOC_CHECKS[@]}"
    print_check_category "Versioning" "${VERSION_CHECKS[@]}"
    print_check_category "API" "${API_CHECKS[@]}"

    # Version info
    if [[ -n "$PACKAGE_VERSION" ]] || [[ -n "$CHANGELOG_VERSION" ]]; then
        print_section "Version Information"
        if [[ -n "$PACKAGE_VERSION" ]]; then
            echo "- package.json: $PACKAGE_VERSION"
        fi
        if [[ -n "$CHANGELOG_VERSION" ]]; then
            echo "- CHANGELOG.md: $CHANGELOG_VERSION"
        fi
        echo "- Consistent: $VERSIONS_CONSISTENT"
        echo ""
    fi
}

# Main execution
main() {
    # Resolve paths
    if ! resolve_paths; then
        exit_unexpected_error "Failed to resolve paths" "Ensure you are in a spec kit project"
    fi

    # Run all checks
    check_artifacts
    check_readme
    check_changelog
    check_versions
    check_api_docs

    # Output checklist
    output_checklist

    # Exit with appropriate code
    if [[ "$FAIL_COUNT" -gt 0 ]]; then
        exit 1
    else
        exit 0
    fi
}

main "$@"
