#!/usr/bin/env bash
# Repository Intelligence CLI Tool
# Copyright (c) 2024 Repository Intelligence Team
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ==============================================================================
# Repository Intelligence TUI Runner (v3.0.0) - Legacy Bash TUI
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."
PYTHON_BIN="${PROJECT_ROOT}/venv/bin/python"
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

# Detect TUI engine (prefer dialog, fallback to whiptail)
if command -v dialog &>/dev/null; then
    TUI_ENGINE="dialog"
elif command -v whiptail &>/dev/null; then
    TUI_ENGINE="whiptail"
else
    echo "[!] Error: Neither 'dialog' nor 'whiptail' is installed."
    echo "    Please install dialog (e.g., brew install dialog / sudo apt install dialog)"
    exit 1
fi

BATCH_FILE="${PROJECT_ROOT}/batch_repos.txt"
TUI_BACKEND="${PROJECT_ROOT}/src/repo_analysis/tui_backend.py"
ANALYZER="${PROJECT_ROOT}/src/repo_analysis/analyzer.py"
OUTPUTS_DIR="${PROJECT_ROOT}/outputs"

show_banner() {
    clear
    echo "============================================================"
    echo "    Repository Intelligence CLI Tool — TUI Launcher"
    echo "============================================================"
    echo ""
}

main_menu() {
    local choice
    choice=$($TUI_ENGINE --clear \
        --backtitle "Repository Intelligence CLI Tool (v3.0.0)" \
        --title "Select Git Platform Provider" \
        --menu "\nSelect operation or provider to fetch repositories from:" 18 70 4 \
        "1" "GitHub (User / Organization)" \
        "2" "Azure DevOps (Organization / Project)" \
        "3" "Summarize High-Rating Repositories (Rating > 5.0 & Label != Poor)" \
        "4" "Exit" \
        3>&1 1>&2 2>&3)
    echo "$choice"
}

show_high_rating_summary() {
    local summary_text
    summary_text=$("$PYTHON_BIN" "$TUI_BACKEND" summarize-rating --output-dir "$OUTPUTS_DIR" --format dialog 2>&1)
    
    local tmp_sum="/tmp/tui_high_rating_summary.txt"
    echo "$summary_text" > "$tmp_sum"
    
    $TUI_ENGINE --clear \
        --backtitle "Repository Intelligence CLI Tool — High Rating Repositories" \
        --title "High-Rating Repositories Summary (Rating > 5.0 & Label != Poor)" \
        --textbox "$tmp_sum" 22 80 || \
    $TUI_ENGINE --clear \
        --backtitle "Repository Intelligence CLI Tool — High Rating Repositories" \
        --title "High-Rating Repositories Summary" \
        --msgbox "$summary_text" 22 80

    rm -f "$tmp_sum"
}

auth_menu() {
    local provider="$1"
    local org_name="$2"
    local choice

    choice=$($TUI_ENGINE --clear \
        --backtitle "Repository Intelligence CLI Tool — Authentication" \
        --title "${provider} Authentication & Web Token Login" \
        --menu "\nChoose authentication option for ${provider}:" 16 70 3 \
        "1" "Web Login (Open Browser to generate & paste PAT)" \
        "2" "Enter Existing Personal Access Token (PAT)" \
        "3" "Anonymous / Public Repos Only (No Token)" \
        3>&1 1>&2 2>&3)
    echo "$choice"
}

get_target_input() {
    local provider="$1"
    local prompt_text
    local target

    if [ "$provider" = "GitHub" ]; then
        prompt_text="Enter GitHub Username or Organization Name:\n(e.g., torvalds, google, facebook, or your username)"
    else
        prompt_text="Enter Azure DevOps Organization Name:\n(e.g., my-company-org)"
    fi

    target=$($TUI_ENGINE --clear \
        --backtitle "Repository Intelligence CLI Tool — Target Selection" \
        --title "${provider} Target Selection" \
        --inputbox "\n${prompt_text}" 14 65 "" \
        3>&1 1>&2 2>&3)

    echo "$target"
}

get_token_input() {
    local token
    token=$($TUI_ENGINE --clear \
        --backtitle "Repository Intelligence CLI Tool — Security" \
        --title "Enter Personal Access Token" \
        --inputbox "\nPaste or enter your Token / PAT:" 12 65 "" \
        3>&1 1>&2 2>&3)
    echo "$token"
}

show_msg() {
    local title="$1"
    local msg="$2"
    $TUI_ENGINE --clear \
        --backtitle "Repository Intelligence CLI Tool" \
        --title "$title" \
        --msgbox "\n$msg" 12 65
}

visibility_menu() {
    local provider="$1"
    local choice
    choice=$($TUI_ENGINE --clear \
        --backtitle "Repository Intelligence CLI Tool — Repository Visibility" \
        --title "${provider} Repository Visibility" \
        --menu "\nSelect repository visibility to fetch:" 15 70 3 \
        "1" "All Repositories (Public + Private)" \
        "2" "Public Repositories Only" \
        "3" "Private Repositories Only" \
        3>&1 1>&2 2>&3)
    echo "$choice"
}

run_tui_flow() {
    while true; do
        PROVIDER_CHOICE=$(main_menu)
        
        if [ "$PROVIDER_CHOICE" = "4" ] || [ -z "$PROVIDER_CHOICE" ]; then
            clear
            echo "Exiting Repository Intelligence TUI. Goodbye!"
            exit 0
        fi

        if [ "$PROVIDER_CHOICE" = "3" ]; then
            show_high_rating_summary
            continue
        fi

        if [ "$PROVIDER_CHOICE" = "1" ]; then
            PROVIDER_NAME="GitHub"
            PROVIDER_KEY="github"
        elif [ "$PROVIDER_CHOICE" = "2" ]; then
            PROVIDER_NAME="Azure DevOps"
            PROVIDER_KEY="azure"
        fi

        # Step 1: Input target org / user
        TARGET_NAME=$(get_target_input "$PROVIDER_NAME")
        if [ -z "$TARGET_NAME" ]; then
            show_msg "Input Error" "Target username or organization cannot be empty."
            continue
        fi

        # Step 2: Authentication
        AUTH_CHOICE=$(auth_menu "$PROVIDER_NAME" "$TARGET_NAME")
        TOKEN=""

        if [ "$AUTH_CHOICE" = "1" ]; then
            WEB_URL=$("$PYTHON_BIN" "$TUI_BACKEND" get-url --provider "$PROVIDER_KEY" --org "$TARGET_NAME")
            show_msg "Web Browser Login" "Opening browser to web token generation page:\n\n${WEB_URL}\n\nClick OK after browser opens, then paste token on next screen."
            "$PYTHON_BIN" "$TUI_BACKEND" open-browser --url "$WEB_URL" &
            TOKEN=$(get_token_input)
        elif [ "$AUTH_CHOICE" = "2" ]; then
            TOKEN=$(get_token_input)
        fi

        # Step 2b: Visibility Selection (only relevant if token provided or for GitHub public orgs)
        VISIBILITY_CHOICE=$(visibility_menu "$PROVIDER_NAME")
        case "$VISIBILITY_CHOICE" in
            "1") VISIBILITY="all" ;;
            "2") VISIBILITY="public" ;;
            "3") VISIBILITY="private" ;;
            *) VISIBILITY="all" ;;
        esac
        
        # If no token and user selects private, warn and fallback to public
        if [ -z "$TOKEN" ] && [ "$VISIBILITY" = "private" ]; then
            show_msg "Warning" "Private repositories require authentication.\nFalling back to Public repositories only."
            VISIBILITY="public"
        fi

        # GitHub-specific warning: private repos only work for orgs (with token) or authenticated user ("me")
        if [ "$PROVIDER_KEY" = "github" ] && [ "$VISIBILITY" = "private" ]; then
            if [ -n "$TOKEN" ]; then
                if [ "$TARGET_NAME" = "me" ] || [ "$TARGET_NAME" = "self" ] || [ "$TARGET_NAME" = "@me" ]; then
                    : # OK - authenticated user can see their own private repos
                else
                    show_msg "GitHub Private Repos" "Note: For GitHub, private repositories are only accessible for:\n  - Your own account (use 'me' as target)\n  - Organizations you have admin access to (with token)\n\nPrivate repos for other users cannot be accessed via API."
                fi
            fi
        fi

        echo "[DEBUG] Selected visibility: $VISIBILITY" >&2

        # Step 2.5: Validate Company / Organization Existence
        clear
        echo "Validating existence of company/organization '${TARGET_NAME}' on ${PROVIDER_NAME}..."
        
        CHECK_CMD=("$PYTHON_BIN" "$TUI_BACKEND" check-company --provider "$PROVIDER_KEY" --target "$TARGET_NAME")
        if [ -n "$TOKEN" ]; then
            CHECK_CMD+=(--token "$TOKEN")
        fi

        CHECK_OUT=$("${CHECK_CMD[@]}" 2>&1) || true
        
        if [[ "$CHECK_OUT" == NOT_FOUND:* ]]; then
            ERR_MSG="${CHECK_OUT#NOT_FOUND:}"
            show_msg "Company / Organization Not Found" "Validation Error:\n\n${ERR_MSG}\n\nPlease check the company/organization name and try again."
            continue
        fi

        # Step 3: Fetching Repositories
        clear
        echo "Fetching repository list from ${PROVIDER_NAME} for '${TARGET_NAME}'..."
        echo "[DEBUG] Fetching with visibility: $VISIBILITY" >&2
        
        FETCH_CMD=("$PYTHON_BIN" "$TUI_BACKEND" fetch-repos --provider "$PROVIDER_KEY" --target "$TARGET_NAME" --visibility "$VISIBILITY" --format dialog)
        if [ -n "$TOKEN" ]; then
            FETCH_CMD+=(--token "$TOKEN")
        fi

        # Don't suppress stderr so we can see debug output
        "${FETCH_CMD[@]}" > /dev/null || true

        # Step 4: Safely read dialog checklist arguments without eval
        checklist_args=()
        while IFS= read -r -d '' tag && IFS= read -r -d '' label && IFS= read -r -d '' status; do
            checklist_args+=("$tag" "$label" "$status")
        done < <("$PYTHON_BIN" "$TUI_BACKEND" get-dialog-args)

        if [ ${#checklist_args[@]} -eq 0 ]; then
            show_msg "No Repositories Found" "Could not retrieve repositories for '${TARGET_NAME}'.\n\nPlease check the target name or token permissions."
            continue
        fi

        SELECTED_TAGS=$($TUI_ENGINE --clear \
            --backtitle "Repository Intelligence CLI Tool — Selection" \
            --title "Select Repositories to Analyze (${PROVIDER_NAME})" \
            --checklist "\nUse [SPACE] to select/deselect repos, [ENTER] to confirm selection:" \
            22 85 12 \
            "${checklist_args[@]}" \
            3>&1 1>&2 2>&3)

        if [ -z "$SELECTED_TAGS" ]; then
            show_msg "Selection Cancelled" "No repositories were selected for batch analysis."
            continue
        fi

        # Step 5: Resolve selected repos to batch file
        RESOLVE_OUT=$("$PYTHON_BIN" "$TUI_BACKEND" resolve-selected --tags "$SELECTED_TAGS" --out "$BATCH_FILE")
        
        COUNT=$(wc -l < "$BATCH_FILE" | tr -d ' ')
        
        if [ "$COUNT" -eq 0 ]; then
            show_msg "Error" "Zero repositories resolved. Returning to main menu."
            continue
        fi

        # Step 6: Batch Analysis Execution
        clear
        echo "============================================================"
        echo "  Starting Batch Analysis on ${COUNT} Repository(ies)"
        echo "============================================================"
        echo "Batch File: ${BATCH_FILE}"
        echo ""

        RUN_CMD=("$PYTHON_BIN" "$ANALYZER" --batch "$BATCH_FILE" -o "$OUTPUTS_DIR")
        if [ -n "$TOKEN" ]; then
            if [ "$PROVIDER_KEY" = "github" ]; then
                RUN_CMD+=(--github-token "$TOKEN")
            elif [ "$PROVIDER_KEY" = "azure" ]; then
                RUN_CMD+=(--azure-token "$TOKEN")
            fi
        fi

        "${RUN_CMD[@]}"

        echo ""
        echo "============================================================"
        echo "  Batch Analysis Complete!"
        echo "============================================================"
        echo "Summary report saved to: ${OUTPUTS_DIR}/summary_all.csv"
        echo "High-rating report saved to: ${OUTPUTS_DIR}/summary_high_rating.csv"
        echo ""

        # Display TUI summary dialog of High Rating Repositories
        show_high_rating_summary
        
        read -r -p "Press [ENTER] to return to main menu or 'q' to quit: " nav_ans
        if [ "$nav_ans" = "q" ] || [ "$nav_ans" = "Q" ]; then
            break
        fi
    done
}

run_tui_flow