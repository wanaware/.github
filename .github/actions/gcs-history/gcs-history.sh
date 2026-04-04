#!/bin/bash
# GCS release history management script - Creates history.json with all releases

update_release_history() {
    local bucket_name="$1"
    local env_prefix="$2"
    local version="$3"
    local version_tag="$4"
    local env_name="$5"
    local release_date="$6"
    local release_notes="$7"
    local service_name="$8"

    local releases_path="gs://${bucket_name}/${service_name}/releases/history.json"
    local existing_releases='{"releases":[]}'
    
    # Download existing releases from GCS if not already present locally
    if [[ -f "output-folder/releases/history.json" ]] && jq empty output-folder/releases/history.json 2>/dev/null; then
        existing_releases=$(cat output-folder/releases/history.json)
    elif gcloud storage cp "$releases_path" ./existing-releases.json 2>/dev/null && jq empty ./existing-releases.json 2>/dev/null; then
        existing_releases=$(cat ./existing-releases.json)
        rm -f ./existing-releases.json
    fi
    
    # Clean release notes to remove control characters and problematic sequences
    local cleaned_release_notes=$(echo "$release_notes" | tr -d '\000-\031\177-\377' | sed 's/\r//g' | sed 's/\x1b\[[0-9;]*m//g')
    
        # Load PR details if available
    local pr_details='[]'
    if [[ -f "pr-details.json" ]] && jq empty pr-details.json 2>/dev/null; then
        # Extract structured PR info: title, summary, why, dependencies
        pr_details=$(jq '[.[] | {
            number: .number,
            title: .title,
            user: .user,
            summary: (
                if .body then
                    ((.body | capture("## Summary[\\s]*(?<s>[\\s\\S]*?)(?=## |$)")) // {"s": ""}) | .s | gsub("<!--[\\s\\S]*?-->"; "") | ltrimstr("\n") | rtrimstr("\n") | gsub("^\\s+|\\s+$"; "")
                else "" end
            ),
            why: (
                if .body then
                    ((.body | capture("## Why[\\s]*(?<w>[\\s\\S]*?)(?=## |$)")) // {"w": ""}) | .w | gsub("<!--[\\s\\S]*?-->"; "") | ltrimstr("\n") | rtrimstr("\n") | gsub("^\\s+|\\s+$"; "")
                else "" end
            ),
            dependencies: (
                if .body then
                    ((.body | capture("## Dependencies[\\s]*(?<d>[\\s\\S]*?)(?=## |$)")) // {"d": ""}) | .d | gsub("<!--[\\s\\S]*?-->"; "") | ltrimstr("\n") | rtrimstr("\n") | gsub("^\\s+|\\s+$"; "")
                else "" end
            )
        }]' pr-details.json 2>/dev/null || echo '[]')
    fi

    local new_release=$(jq -n \
        --arg version "$version" \
        --arg versionTag "$version_tag" \
        --arg environment "$env_name" \
        --arg releaseDate "$(date --iso-8601=seconds)" \
        --arg releaseNotes "$cleaned_release_notes" \
        --argjson prDetails "$pr_details" \
        '{
            version: $version,
            versionTag: $versionTag,
            environment: $environment,
            releaseDate: $releaseDate,
            releaseNotes: $releaseNotes,
            prDetails: $prDetails
        }'
    )
    
    # Update releases (keep latest 30)
    local updated_releases=$(echo "$existing_releases" | jq --argjson newRelease "$new_release" '
        .releases = [$newRelease] + (.releases // []) |
        .releases = .releases[0:30]
    ')
    
    # Save updated releases to output folder
    mkdir -p output-folder/releases
    echo "$updated_releases" > output-folder/releases/history.json
    
    # Generate HTML dashboard
    generate_html_dashboard "$updated_releases" "$bucket_name" "$service_name"
}

generate_html_dashboard() {
    local releases_data="$1"
    local bucket_name="$2"
    local service_name="$3"
    
    # Create HTML dashboard
    cat > latest.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>SERVICE_NAME_PLACEHOLDER - Release Dashboard</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        .header h1 {
            margin: 0 0 10px 0;
            font-size: 2.5em;
            font-weight: 700;
        }
        .header h2 {
            margin: 0 0 10px 0;
            font-size: 1.5em;
            font-weight: 400;
            opacity: 0.9;
        }
        .header p {
            margin: 0;
            opacity: 0.8;
            font-size: 1.1em;
        }
        .content {
            padding: 40px;
        }
        .latest-release {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 16px;
            padding: 35px;
            margin-bottom: 50px;
            color: white;
            box-shadow: 0 12px 35px rgba(102, 126, 234, 0.4);
            position: relative;
            overflow: hidden;
            border: 3px solid rgba(255, 255, 255, 0.2);
        }
        .latest-release::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%);
            pointer-events: none;
        }
        .latest-release::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #ff6b6b, #feca57, #48dbfb, #ff9ff3);
            background-size: 400% 100%;
            animation: shimmer 3s ease-in-out infinite;
        }
        @keyframes shimmer {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }
        .latest-badge {
            display: inline-block;
            background: rgba(255, 255, 255, 0.25);
            padding: 8px 20px;
            border-radius: 25px;
            font-size: 0.9em;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 20px;
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        .history-section {
            margin-top: 30px;
            padding-top: 30px;
            border-top: 3px solid #e9ecef;
            position: relative;
        }
        .history-section::before {
            content: '';
            position: absolute;
            top: -2px;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, #667eea, #764ba2);
        }
        .release-card {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
            border-left: 4px solid #e9ecef;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            position: relative;
            overflow: hidden;
        }
        .release-card::before {
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 4px;
            background: linear-gradient(180deg, #e9ecef, #667eea);
            transition: all 0.3s ease;
        }
        .release-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.12);
        }
        .release-card:hover::before {
            width: 6px;
            background: linear-gradient(180deg, #667eea, #764ba2);
        }
        .release-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            flex-wrap: wrap;
            gap: 10px;
        }
        .release-title {
            font-size: 1.3em;
            font-weight: 700;
            color: #2c3e50;
        }
        .latest-release .release-title {
            color: white;
            font-size: 1.5em;
        }
        .release-env {
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .env-production { background: #d4edda; color: #155724; }
        .env-staging { background: #fff3cd; color: #856404; }
        .env-development { background: #cce5ff; color: #004085; }
        .latest-release .release-env {
            background: rgba(255, 255, 255, 0.9);
            color: #2c3e50;
        }
        .release-date {
            color: #666;
            font-size: 0.95em;
            font-weight: 500;
            margin-bottom: 15px;
        }
        .latest-release .release-date {
            color: rgba(255, 255, 255, 0.9);
        }
        .release-notes {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-top: 15px;
            line-height: 1.7;
            border: 1px solid #e9ecef;
            font-size: 0.95em;
        }
        .latest-release .release-notes {
            background: rgba(255, 255, 255, 0.95);
            color: #2c3e50;
            backdrop-filter: blur(10px);
        }
        .history-section {
            margin-top: 20px;
        }
        .history-title {
            font-size: 1.8em;
            font-weight: 700;
            color: #2c3e50;
            margin-bottom: 25px;
            text-align: center;
            position: relative;
        }
        .history-title::after {
            content: '';
            position: absolute;
            bottom: -10px;
            left: 50%;
            transform: translateX(-50%);
            width: 60px;
            height: 3px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 2px;
        }
        .footer {
            background: #f8f9fa;
            padding: 25px;
            text-align: center;
            color: #666;
            border-top: 1px solid #e9ecef;
            font-size: 0.9em;
        }
        .changelog-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .changelog-item {
            padding: 12px 0;
            border-bottom: 1px solid rgba(0,0,0,0.08);
        }
        .changelog-item:last-child {
            border-bottom: none;
        }
        .changelog-item-header {
            display: flex;
            align-items: center;
            cursor: pointer;
            user-select: none;
            gap: 10px;
        }
        .changelog-item-header:hover {
            color: #667eea;
        }
        .changelog-toggle {
            font-size: 0.7em;
            transition: transform 0.2s ease;
            color: #667eea;
            flex-shrink: 0;
        }
        .changelog-toggle.expanded {
            transform: rotate(90deg);
        }
        .changelog-item-title {
            font-weight: 500;
        }
        .changelog-item-details {
            display: none;
            margin-top: 10px;
            margin-left: 22px;
            padding: 12px 16px;
            background: #f0f2f5;
            border-radius: 8px;
            font-size: 0.9em;
            line-height: 1.6;
            border-left: 3px solid #667eea;
        }
        .latest-release .changelog-item-details {
            background: rgba(255, 255, 255, 0.85);
        }
        .changelog-item-details.visible {
            display: block;
        }
        .detail-section {
            margin-bottom: 8px;
        }
        .detail-section:last-child {
            margin-bottom: 0;
        }
        .detail-label {
            font-weight: 600;
            color: #555;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 2px;
        }
        .detail-value {
            color: #333;
        }
        @media (max-width: 768px) {
            .content { padding: 20px; }
            .latest-release { padding: 20px; }
            .release-header { flex-direction: column; align-items: flex-start; }
            .release-env { margin-top: 10px; }
            .header { padding: 30px 20px; }
            .header h1 { font-size: 2em; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 SERVICE_NAME_PLACEHOLDER</h1>
            <h2>Release Dashboard</h2>
            <p>Deployment and Release History</p>
        </div>
        
        <div class="content">
            <div id="latest-release"></div>
            <div class="history-section">
                <h3 class="history-title">📚 Release History</h3>
                <div id="release-history"></div>
            </div>
        </div>
        
        <div class="footer">
        </div>
    </div>

    <script>
        const releaseData = RELEASE_DATA_PLACEHOLDER;
        
        function formatDate(dateString) {
            return new Date(dateString).toLocaleString(undefined, {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        }

        function getEnvClass(environment) {
            switch(environment.toLowerCase()) {
                case 'production': return 'env-production';
                case 'staging': return 'env-staging';
                case 'development': return 'env-development';
                default: return 'env-development';
            }
        }

        function isValidPRTitle(title) {
            const regexWithTicket = /^(feat|bug|task)\([A-Z]+-[0-9]+\): .+/;
            const regexWithoutTicket = /^(fix|chore): .+/;
            return regexWithTicket.test(title) || regexWithoutTicket.test(title);
        }

        function cleanReleaseNotes(notes) {
            if (!notes) return 'No release notes available';
            
            // Remove Full Changelog section
            let cleaned = notes.replace(/\*\*Full Changelog\*\*:.*$/gm, '');
            
            // Fix common formatting issues in GitHub generated release notes
            cleaned = cleaned.replace(/## What's Changed\*/, '## What\'s Changed\n*');
            cleaned = cleaned.replace(/\* /g, '\n* ');
            
            // Process PR entries - extract titles and validate them
            const lines = cleaned.split('\n');
            const validPRs = [];
            
            lines.forEach(line => {
                const trimmed = line.trim();
                if (trimmed.startsWith('* ')) {
                    // Extract PR title (everything before " by @")
                    let prTitle = trimmed.substring(2);
                    prTitle = prTitle.replace(/ by @.*$/, '').trim();
                    prTitle = prTitle.replace(/ in https:\/\/github\.com\/.*$/, '').trim();
                    
                    // Use validation to filter out invalid PR titles and exclude chore PRs
                    if (prTitle.length > 0 && isValidPRTitle(prTitle) && !prTitle.startsWith('chore:')) {
                        validPRs.push(prTitle);
                    }
                } else if (trimmed && !trimmed.includes('What\'s Changed') && !trimmed.includes('**Full Changelog**')) {
                    // Keep other relevant lines only if they look like valid PR titles and are not chore PRs
                    if (trimmed !== '## What\'s Changed' && isValidPRTitle(trimmed) && !trimmed.startsWith('chore:')) {
                        validPRs.push(trimmed);
                    }
                }
            });
            
            // Sort PRs to show latest first
            validPRs.sort((a, b) => {
                const getNumber = (title) => {
                    const match = title.match(/testing\s+(\d+)/);
                    return match ? parseInt(match[1]) : 0;
                };
                
                const numA = getNumber(a);
                const numB = getNumber(b);
                
                if (numA && numB) {
                    return numB - numA; // Higher numbers first (newer)
                }
                
                return 0;
            });
            
            // Join valid PRs with bullet points
            cleaned = validPRs.map(pr => `• ${pr}`).join('\n').trim();
            
            // Fallback: simple cleanup if no valid PRs found
            if (!cleaned) {
                const fallbackLines = notes
                    .replace(/\*\*Full Changelog\*\*:.*$/gm, '')
                    .replace(/https:\/\/github\.com\/[^\s]*/g, '')
                    .replace(/by @[^\s]*/g, '')
                    .replace(/## What's Changed/g, '')
                    .split('\n')
                    .map(line => line.trim())
                    .filter(line => line && isValidPRTitle(line) && !line.startsWith('chore:'));
                
                if (fallbackLines.length > 0) {
                    cleaned = fallbackLines.map(pr => `• ${pr}`).join('\n');
                }
            }
            
            return cleaned || '';
        }

        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function findPRDetail(prDetails, title) {
            if (!prDetails || !Array.isArray(prDetails)) return null;
            return prDetails.find(pr => title.includes(pr.title) || (pr.number && title.includes('#' + pr.number)));
        }

        function renderDetailSections(detail) {
            if (!detail) return '';
            let html = '';

            if (detail.summary && detail.summary.trim() && detail.summary.trim().toLowerCase() !== 'none') {
                html += '<div class="detail-section"><div class="detail-label">Summary</div><div class="detail-value">' + escapeHtml(detail.summary) + '</div></div>';
            }
            if (detail.why && detail.why.trim() && detail.why.trim().toLowerCase() !== 'none') {
                html += '<div class="detail-section"><div class="detail-label">Why</div><div class="detail-value">' + escapeHtml(detail.why) + '</div></div>';
            }
            if (detail.dependencies && detail.dependencies.trim() && detail.dependencies.trim().toLowerCase() !== 'none') {
                html += '<div class="detail-section"><div class="detail-label">Dependencies</div><div class="detail-value">' + escapeHtml(detail.dependencies) + '</div></div>';
            }

            return html;
        }

        function formatChangelogItems(notes, prDetails) {
            if (!notes || notes.trim() === '') return '';

            const lines = notes.split('\n').filter(line => line.trim() !== '');
            if (lines.length === 0) return '';

            const items = lines.map(line => {
                const cleaned = line.replace(/^[•*\-]\s*/, '').trim();
                return cleaned;
            }).filter(item => item !== '');

            if (items.length === 0) return '';

            const listItems = items.map((item) => {
                const detail = findPRDetail(prDetails, item);
                const detailHtml = renderDetailSections(detail);
                const hasDetails = detailHtml.length > 0;
                const itemId = 'pr-detail-' + Math.random().toString(36).substr(2, 9);

                if (hasDetails) {
                    return '<li class="changelog-item">' +
                        '<div class="changelog-item-header" onclick="toggleDetail(\'' + itemId + '\', this)">' +
                        '<span class="changelog-toggle">▶</span>' +
                        '<span class="changelog-item-title">' + escapeHtml(item) + '</span>' +
                        '</div>' +
                        '<div class="changelog-item-details" id="' + itemId + '">' + detailHtml + '</div>' +
                        '</li>';
                } else {
                    return '<li class="changelog-item">' +
                        '<div class="changelog-item-header" style="cursor:default;">' +
                        '<span class="changelog-toggle" style="visibility:hidden;">▶</span>' +
                        '<span class="changelog-item-title">' + escapeHtml(item) + '</span>' +
                        '</div>' +
                        '</li>';
                }
            }).join('');

            return '<ul class="changelog-list">' + listItems + '</ul>';
        }

        function toggleDetail(id, headerEl) {
            const el = document.getElementById(id);
            const toggle = headerEl.querySelector('.changelog-toggle');
            if (el.classList.contains('visible')) {
                el.classList.remove('visible');
                toggle.classList.remove('expanded');
            } else {
                el.classList.add('visible');
                toggle.classList.add('expanded');
            }
        }

        function renderLatestRelease(release) {
            const cleanedNotes = cleanReleaseNotes(release.releaseNotes);
            const formattedNotes = formatChangelogItems(cleanedNotes, release.prDetails);
            
            return `
                <div class="latest-release">
                    <div class="latest-badge">🌟 Latest Release</div>
                    <div class="release-header">
                        <div class="release-title">${release.versionTag}</div>
                        <div class="release-env ${getEnvClass(release.environment)}">${release.environment}</div>
                    </div>
                    <div class="release-date">Released: ${formatDate(release.releaseDate)}</div>
                    ${formattedNotes ? `<div class="release-notes">${formattedNotes}</div>` : ''}
                </div>
            `;
        }

        function renderHistoryRelease(release) {
            const cleanedNotes = cleanReleaseNotes(release.releaseNotes);
            const formattedNotes = formatChangelogItems(cleanedNotes, release.prDetails);
            
            return `
                <div class="release-card">
                    <div class="release-header">
                        <div class="release-title">${release.versionTag}</div>
                        <div class="release-env ${getEnvClass(release.environment)}">${release.environment}</div>
                    </div>
                    <div class="release-date">Released: ${formatDate(release.releaseDate)}</div>
                    ${formattedNotes ? `<div class="release-notes">${formattedNotes}</div>` : ''}
                </div>
            `;
        }

        function loadReleases() {
            if (releaseData && releaseData.releases && releaseData.releases.length > 0) {
                // Show latest release
                document.getElementById('latest-release').innerHTML = renderLatestRelease(releaseData.releases[0]);
                
                // Show historical releases (excluding the first one)
                const historicalReleases = releaseData.releases.slice(1);
                if (historicalReleases.length > 0) {
                    const historyHtml = historicalReleases.map(release => renderHistoryRelease(release)).join('');
                    document.getElementById('release-history').innerHTML = historyHtml;
                } else {
                    document.getElementById('release-history').innerHTML = '<p style="text-align: center; color: #666; font-style: italic;">No historical releases available</p>';
                }
                
                // Update last updated time
                document.getElementById('last-updated').textContent = formatDate(releaseData.releases[0].releaseDate);
                
                // Update cache version if available
                if (releaseData.cacheVersion) {
                    document.getElementById('cache-version').textContent = releaseData.cacheVersion;
                }
            } else {
                document.getElementById('latest-release').innerHTML = '<p style="text-align: center; color: #666;">No releases found.</p>';
                document.getElementById('release-history').innerHTML = '<p style="text-align: center; color: #666;">No release history available.</p>';
                document.getElementById('last-updated').textContent = 'Never';
            }
        }

        document.addEventListener('DOMContentLoaded', function() {
            loadReleases();
        });
    </script>
</body>
</html>
EOF

    # Replace service name placeholder in the generated HTML
    sed -i "s/SERVICE_NAME_PLACEHOLDER/${service_name}/g" latest.html

    # Save the JSON data to a temporary file to avoid shell escaping issues
    echo "$releases_data" > temp_releases.json
    
    # Use Python to safely replace the placeholder with JSON data and save to output folder
    python3 -c "
import sys
import json
import os
from datetime import datetime, timezone

try:
    # Read the HTML file
    with open('latest.html', 'r') as f:
        html_content = f.read()

    # Read and validate the JSON data from file
    with open('temp_releases.json', 'r') as f:
        json_data = f.read()
    
    # Clean the JSON data to remove control characters
    import re
    # Remove control characters except newlines and tabs
    json_data = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', json_data)
    
    # Parse to validate JSON
    parsed_json = json.loads(json_data)
    
    # Add cache-busting timestamp to the JSON
    parsed_json['lastUpdated'] = datetime.now(timezone.utc).isoformat()
    parsed_json['cacheVersion'] = str(int(datetime.now(timezone.utc).timestamp()))
    
    # Replace the placeholder with the actual JSON data
    html_content = html_content.replace('const releaseData = RELEASE_DATA_PLACEHOLDER;', 'const releaseData = ' + json.dumps(parsed_json, indent=2) + ';')

    # Create output folder if it doesn't exist
    os.makedirs('output-folder/releases', exist_ok=True)
    
    # Write the updated HTML file directly to output folder
    with open('output-folder/releases/latest.html', 'w') as f:
        f.write(html_content)
    
except Exception as e:
    print(f'Error processing data: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"
    
    # Clean up temporary files
    rm -f latest.html temp_releases.json
}

# Execute if called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    update_release_history "$@"
fi
