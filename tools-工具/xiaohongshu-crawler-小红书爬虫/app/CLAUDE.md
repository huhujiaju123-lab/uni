# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Last Updated:** 2024-12-12
**Current Version:** 3.0.0
**Status:** Ready for distribution testing / Chrome Web Store submission

---

## Project Overview

A Chrome extension (Manifest V3) that automatically monitors and extracts Xiaohongshu (小红书) notes data including post details and comments. Features dual-mode auto-capture (list pages + detail pages) with local storage and CSV export.

**Key Features:**
- 🚀 One-click auto-monitoring system
- 📋 Dual-mode capture (list pages + detail pages)
- 💬 Comment extraction with formatting
- 📊 CSV export functionality
- 🔒 100% local storage (no data upload)
- 🌍 Cross-platform compatible

---

## Current Project Status

### ✅ Completed

**Core Development:**
- [x] All extension functionality implemented
- [x] Auto-monitoring system with URL detection
- [x] List page and detail page extraction
- [x] Comment formatting with line breaks
- [x] CSV export with proper encoding
- [x] Cross-platform compatibility verified

**Packaging & Distribution:**
- [x] Author field updated to "xiaoxiao"
- [x] Icons generated (temporary purple gradient circles)
- [x] Extension packaged: `xiaohongshu-crawler-v3.0.zip` (18KB)
- [x] Distribution package created: `xiaohongshu-crawler-测试版.zip` (24KB)

**Documentation:**
- [x] README.md - Project documentation
- [x] PRIVACY_POLICY.md - Privacy policy for Chrome Web Store
- [x] 安装说明.txt - User installation guide
- [x] 测试反馈表.txt - Test feedback form
- [x] 分发测试指南.md - Distribution testing guide
- [x] Chrome商店上架实操指南.md - Chrome Web Store submission guide
- [x] 跨平台兼容性报告.md - Cross-platform compatibility report

**Testing:**
- [x] Test environment created: `test-extension/`
- [x] Test guides prepared
- [x] Quick test checklist available

### 🔄 In Progress

- [ ] User acceptance testing (pending user feedback)
- [ ] Screenshot creation for Chrome Web Store (1280x800)
- [ ] Promotional tile creation (440x280)
- [ ] Privacy policy hosting (GitHub Pages/Notion)

### 📋 Next Steps

**Option A: Continue Distribution Testing**
1. Send `xiaohongshu-crawler-测试版.zip` to test users
2. Collect feedback via 测试反馈表.txt
3. Fix any issues discovered
4. Iterate and retest

**Option B: Submit to Chrome Web Store**
1. Create screenshots and promotional materials
2. Host privacy policy online
3. Register developer account ($5 fee)
4. Submit extension for review
5. Reference: `Chrome商店上架实操指南.md`

---

## Development Setup

### Loading the Extension Locally

```bash
# Method 1: Load unpacked (development)
1. Open Chrome: chrome://extensions/
2. Enable "Developer mode" (toggle top right)
3. Click "Load unpacked"
4. Select project directory

# Method 2: Load from test package
1. Extract test-extension/ or xiaohongshu-crawler-v3.0.zip
2. Follow Method 1 steps with extracted folder

# After code changes:
# - Click reload icon on chrome://extensions/
# - Refresh xiaohongshu.com page to test
```

### Packaging for Distribution

```bash
# Package extension
./package.sh

# Output: xiaohongshu-crawler-v3.0.zip (18KB)
# - Includes all necessary files
# - Checks for required icon files
# - Auto-cleans temporary files (.DS_Store, etc)
```

### Creating Distribution Package

```bash
# Full distribution package with user guides
# Already created: xiaohongshu-crawler-测试版.zip (24KB)

# Contents:
# - xiaohongshu-crawler-v3.0.zip (extension package)
# - 安装说明.txt (installation guide)
# - 测试反馈表.txt (feedback form)
# - 请先阅读我.txt (important notice)
```

---

## Architecture

### Chrome Extension Components

**manifest.json** - Extension configuration
- Manifest V3 standard
- Version: 3.0.0
- Author: xiaoxiao
- Permissions: `storage`, `activeTab`
- Host permissions: xiaohongshu.com only
- Icons: 16, 32, 48, 128px (currently temporary icons)

**background.js** - Service Worker
- Handles messages from content scripts
- Manages data persistence via Chrome Storage API
- Actions:
  - `saveListData` - Save and deduplicate list page data
  - `saveDetailData` - Save and deduplicate detail page data
- All data processing is local-only (no network calls)
- Deduplication based on link (list) or URL (detail)

**content/content.js** - Content Script (runs on xiaohongshu.com)
- Injected into xiaohongshu.com pages automatically
- **Auto-monitoring system (lines 386-514):**
  - `autoMonitorEnabled` - Monitor state flag
  - `currentPageType` - 'list' | 'detail' | 'unknown'
  - `lastProcessedNotes` - Deduplication Set
  - `startAutoMonitor()` - Enable auto-capture
  - `stopAutoMonitor()` - Disable auto-capture
  - `detectPageType()` - Page type detection
  - URL change detection via setInterval (1s)
  - MutationObserver for DOM changes on list pages

- **Data extraction functions:**
  - `autoScrollToLoadAll()` - Auto-scroll to load all notes
  - `getNoteDataFromDOM()` - Extract list page data
  - `getNoteDetailData()` - Extract detail page data with fallback strategies
  - `autoCaptureListPage()` - Auto-capture list data
  - `autoCapturDetailPage()` - Auto-capture detail data

- **Message listeners:**
  - `crawlData` - Manual list page capture
  - `crawlDetail` - Manual detail page capture
  - `startAutoMonitor` - Enable auto-monitor
  - `stopAutoMonitor` - Disable auto-monitor
  - `getMonitorStatus` - Query current status

**popup/** - User Interface
- `popup.html` - Extension popup interface
  - Auto-monitor section (purple gradient)
  - Manual capture buttons
  - Tabbed data display (list/detail)
  - Download button for CSV export

- `popup.js` - UI logic and state management
  - Monitor toggle functionality
  - Status update polling (every 2 seconds)
  - Data display with pagination
  - Enhanced comment display with formatting
  - CSV generation and download

- `popup.css` - Styling
  - Purple gradient auto-monitor section
  - Active/inactive button states
  - Tab navigation styles
  - Responsive layout

### Data Flow

**1. Auto-Capture Mode (Recommended):**
```
User clicks "🚀 启动自动监控" in popup
    ↓
Popup sends "startAutoMonitor" message to content script
    ↓
Content script:
  - Sets autoMonitorEnabled = true
  - Detects current page type (list/detail)
  - Starts URL monitoring (setInterval)
  - Starts DOM monitoring (MutationObserver)
    ↓
On page navigation or DOM change:
  - Detects new page type
  - Executes appropriate extractor:
    • autoCaptureListPage() → getNoteDataFromDOM()
    • autoCapturDetailPage() → getNoteDetailData()
    ↓
Extracted data sent to background.js via chrome.runtime.sendMessage
    ↓
Background.js saves to chrome.storage.local with deduplication
    ↓
Popup displays updated data (refreshed every 2s or on manual refresh)
```

**2. Manual Capture:**
```
User clicks "抓取列表页笔记" or "抓取当前详情页"
    ↓
Popup sends message to content script
    ↓
Content script extracts data and responds
    ↓
Popup receives data and saves to storage
    ↓
Display refreshes to show new data
```

**3. Data Storage Schema:**
```javascript
// chrome.storage.local.noteData (Array)
{
  author: string,      // "用户名"
  like: string,        // "1234" (点赞数)
  title: string,       // "笔记标题"
  link: string         // "https://www.xiaohongshu.com/explore/..."
}

// chrome.storage.local.detailData (Array)
{
  url: string,                // 笔记URL (用于去重)
  contentTitle: string,       // 笔记标题
  content: string,            // 笔记正文
  comments: [{                // 评论列表
    index: number,            // 评论序号
    username: string,         // 评论用户名
    content: string,          // 评论内容
    likes: string             // 评论点赞数
  }],
  commentsCount: number       // 评论总数
}
```

### DOM Extraction Strategy

Uses **multiple fallback strategies** for robustness against Xiaohongshu DOM changes:

**Title Extraction (3 strategies):**
1. Find h1/title class elements (filter out "小红书")
2. Search main content area for headings
3. Extract from document.title and clean up

**Content Extraction (2 strategies):**
1. Find desc/content class elements with length > 10 chars
2. Find longest text block (50-5000 chars, exclude navigation/buttons)

**Comment Extraction (multi-tier strategy):**
1. Locate comment container by class pattern matching: `[class*="comment"]`
2. Find comment items within container
3. Fallback: Find all divs with appropriate text length
4. Extract for each comment:
   - Username (multiple selector fallback)
   - Content (full text)
   - Likes (regex match with k/m conversion)
5. Deduplicate by content to avoid duplicates

**List Page Extraction:**
- Find note cards using composite selectors
- Filter to innermost cards (avoid parent containers)
- Extract: author, like count, title, link
- Deduplicate by link

---

## Key Constraints

### Platform Compatibility ✅

**100% cross-platform compatible:**
- No absolute paths (all relative)
- No OS-specific code (no `process.platform`, etc)
- No file system operations (all via Chrome Storage API)
- No build tools required (pure JavaScript)
- Only Web Standard APIs and Chrome Extension APIs
- UTF-8 encoding throughout

**Verified on:**
- macOS ✅
- Windows ✅ (compatible, pending user testing)
- Linux ✅ (compatible, pending user testing)
- Chrome OS ✅ (compatible)

### Privacy & Security

**Core principles:**
- **100% local storage** - All data in chrome.storage.local
- **Zero data upload** - No external API calls or network requests
- **No tracking** - No analytics, telemetry, or tracking scripts
- **Minimal permissions** - Only storage and activeTab
- **Domain-restricted** - Only runs on xiaohongshu.com

**Security considerations:**
- No eval() or dynamic code execution
- No inline scripts (CSP compliant)
- No access to user credentials or sensitive data
- All data user-controlled (can be cleared anytime)

### Permissions Justification

**storage:**
- Purpose: Local data persistence in browser
- Usage: Save extracted notes and comments
- Scope: chrome.storage.local only
- No remote sync or upload

**activeTab:**
- Purpose: Read xiaohongshu.com page content
- Usage: Only activated when user clicks extension icon or enables auto-monitor
- Scope: Current active tab only
- No background monitoring of other tabs

**host_permissions (xiaohongshu.com):**
- Purpose: Run content script on Xiaohongshu only
- Usage: Extract public post information
- Scope: xiaohongshu.com domain only
- No access to other websites

---

## Testing Workflow

### Local Development Testing

```bash
# 1. Load extension
chrome://extensions/ → Load unpacked → Select project directory

# 2. Open console for debugging
F12 → Console tab (watch for [自动监控] and [自动抓取] logs)

# 3. Navigate to test site
https://www.xiaohongshu.com

# 4. Test auto-monitor mode
- Click extension icon
- Click "🚀 启动自动监控"
- Browse list pages (watch console)
- Click into note details (watch console)
- Verify data in popup tabs

# 5. Test manual mode
- Click "抓取列表页笔记" on list page
- Click "抓取当前详情页" on detail page
- Verify success alerts and data

# 6. Test CSV export
- Click "下载所有数据"
- Open CSV in Excel/Numbers
- Verify data completeness and encoding
```

### User Acceptance Testing

**Test package location:**
```
xiaohongshu-crawler-测试版.zip (24KB)
```

**Test procedure:**
1. Send distribution package to test users
2. Users follow 安装说明.txt to install
3. Users test functionality (10-15 minutes)
4. Users fill out 测试反馈表.txt
5. Collect and analyze feedback
6. Fix critical issues and retest

**Success criteria:**
- 90%+ successful installation rate
- 95%+ functionality working correctly
- 4+ star user satisfaction
- 70%+ willing to recommend

**Reference:** 分发测试指南.md for complete testing workflow

---

## Common Modification Points

### Adding New Data Fields

**1. Update extraction logic:**
```javascript
// In content/content.js
function getNoteDataFromDOM() {
  // Add new field extraction
  let newField = extractNewField(card);
  noteData.push({
    author, like, title, link,
    newField  // Add here
  });
}
```

**2. Update storage schema:**
```javascript
// Data structure automatically extends
// No schema migration needed for chrome.storage.local
```

**3. Update popup display:**
```javascript
// In popup/popup.js - loadSavedData()
tr.innerHTML = `
  <td>${item.author}</td>
  <td>${item.like}</td>
  <td>${item.title}</td>
  <td>${item.newField}</td>  // Add column
  <td><a href="${item.link}">Link</a></td>
`;
```

**4. Update CSV export:**
```javascript
// In popup/popup.js - convertToCSV()
const headers = ['作者', '点赞数', '标题', '新字段', '链接'];
return [author, like, title, newField, link].join(',');
```

### Adjusting DOM Selectors

**When Xiaohongshu updates their HTML:**

1. **Inspect page structure** (F12 → Elements)
2. **Update selectors** in content.js:
   ```javascript
   // Old selector
   const titleElements = card.querySelectorAll('a.title');

   // New selector (add fallback)
   const titleElements = card.querySelectorAll(
     'a.title, a.note-title, a[class*="title"]'
   );
   ```
3. **Test with console.log** to verify extraction
4. **Use multiple strategies** for critical fields

### Modifying UI

**Popup interface changes:**

1. **Structure** - Edit `popup/popup.html`
   ```html
   <button id="newButton">新功能</button>
   ```

2. **Styling** - Edit `popup/popup.css`
   ```css
   #newButton {
     background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
   }
   ```

3. **Behavior** - Edit `popup/popup.js`
   ```javascript
   document.getElementById('newButton').addEventListener('click', () => {
     // Handle click
   });
   ```

4. **Reload extension** to see changes

### Updating Version

**Before releasing new version:**

1. **Update version number:**
   ```json
   // manifest.json
   "version": "3.1.0"  // Increment version
   ```

2. **Update CLAUDE.md:**
   - Update "Current Version" at top
   - Add to version history

3. **Repackage:**
   ```bash
   ./package.sh
   # Creates xiaohongshu-crawler-v3.1.zip
   ```

4. **Test thoroughly** before distribution

---

## File Structure

```
xiaohongshu-crawler/
├── manifest.json                          # Extension config
├── background.js                          # Service worker
├── content/
│   └── content.js                         # Content script (抓取逻辑)
├── popup/
│   ├── popup.html                         # UI structure
│   ├── popup.js                           # UI logic
│   └── popup.css                          # Styling
├── icons/
│   ├── icon16.png                         # 16x16 icon
│   ├── icon32.png                         # 32x32 icon
│   ├── icon48.png                         # 48x48 icon
│   ├── icon128.png                        # 128x128 icon
│   └── icon-generator.html                # Icon generation tool
│
├── xiaohongshu-crawler-v3.0.zip          # Packaged extension (18KB)
├── xiaohongshu-crawler-测试版.zip         # Distribution package (24KB)
│
├── README.md                              # Project documentation
├── CLAUDE.md                              # This file
├── PRIVACY_POLICY.md                      # Privacy policy
│
├── 安装说明.txt                            # User installation guide
├── 测试反馈表.txt                          # Test feedback form
├── 分发测试指南.md                         # Distribution testing guide
├── Chrome商店上架实操指南.md               # Chrome Web Store guide
├── 跨平台兼容性报告.md                     # Compatibility report
├── 上架指南.md                             # Publishing guide
├── 上架清单.md                             # Publishing checklist
├── STORE_LISTING.md                       # Store listing content
├── 发布检查清单.md                         # Release checklist
├── 分发说明.md                             # Distribution instructions
├── 测试指南.md                             # Complete testing guide
├── 测试结果反馈表.md                       # Test results form
├── 上架准备状态.md                         # Publishing readiness status
│
├── test-extension/                        # Test environment
│   ├── manifest.json                      # (Extracted from ZIP)
│   ├── background.js
│   ├── content/
│   ├── popup/
│   ├── icons/
│   └── 快速测试清单.txt                    # Quick test checklist
│
├── package.sh                             # Packaging script
└── .gitignore                             # (if using Git)
```

---

## Important Files Reference

### Core Code Files
- **manifest.json** - Extension configuration (v3.0.0, author: xiaoxiao)
- **background.js** - Service worker (data persistence)
- **content/content.js** - Main extraction logic (587 lines)
- **popup/popup.js** - UI logic (374 lines)

### Distribution Files
- **xiaohongshu-crawler-v3.0.zip** - Extension package (18KB)
- **xiaohongshu-crawler-测试版.zip** - Distribution package (24KB)

### Documentation Files (User-Facing)
- **安装说明.txt** - Installation guide for end users
- **测试反馈表.txt** - Feedback form for testers
- **请先阅读我.txt** - Important notice in distribution package

### Documentation Files (Developer-Facing)
- **CLAUDE.md** - This file (development context)
- **README.md** - Project overview
- **分发测试指南.md** - Distribution testing workflow
- **Chrome商店上架实操指南.md** - Step-by-step Chrome Web Store submission
- **跨平台兼容性报告.md** - Cross-platform compatibility analysis

### Policy Files
- **PRIVACY_POLICY.md** - Privacy policy (required for Chrome Web Store)
- **STORE_LISTING.md** - Chrome Web Store listing content

---

## Version History

### v3.0.0 (2024-12-12) - Current
**Major Features:**
- ✨ Full auto-monitoring system with URL and DOM detection
- 📋 Dual-mode capture (list + detail pages)
- 💬 Comment extraction with formatting
- 📊 CSV export with UTF-8 encoding
- 🎨 Enhanced UI with purple gradient monitor section
- 🔄 Real-time status updates

**Infrastructure:**
- 🔧 Author field updated to "xiaoxiao"
- 📦 Distribution packages created
- 📚 Comprehensive documentation suite
- 🧪 Testing environment prepared
- 🌍 Cross-platform compatibility verified

**Status:** Ready for distribution testing / Chrome Web Store submission

### v2.0 (Initial Development)
- Basic list page scraping
- Manual detail page capture
- Initial comment extraction
- Simple CSV export

---

## Known Issues & Limitations

### Current Limitations

1. **Icons are temporary**
   - Currently using Python-generated purple circles
   - Functional but not professionally designed
   - Can be upgraded using icons/icon-generator.html

2. **Xiaohongshu DOM dependency**
   - Relies on current Xiaohongshu HTML structure
   - May break if they significantly change their website
   - Mitigated by multi-strategy extraction with fallbacks

3. **No data sync**
   - Data stored locally in browser only
   - Not synced across devices
   - User must export CSV to transfer data

4. **Chrome-only**
   - Built for Chrome/Chromium browsers
   - Not compatible with Firefox (different extension API)
   - Works on Edge, Brave, Opera (Chromium-based)

### Potential Improvements

**Performance:**
- Add debouncing to MutationObserver (currently fires frequently)
- Implement virtual scrolling for large data sets in popup
- Cache parsed data to reduce re-parsing

**Features:**
- Add data filtering (by likes, date, author)
- Add search functionality within captured data
- Export format options (JSON, Excel)
- Batch delete functionality
- Import previously exported data

**UX:**
- Add onboarding tutorial for first-time users
- Keyboard shortcuts for common actions
- Progress indicator during capture
- Better error messages with recovery suggestions

**Technical:**
- Add automated tests
- Implement data schema versioning
- Add data backup/restore functionality
- Better icon design (professional branding)

---

## Troubleshooting Guide

### Common Issues

**Issue: Extension icon not showing**
- **Cause:** Icon files missing or corrupted
- **Solution:** Regenerate icons using icons/icon-generator.html
- **Verify:** Check icons/ folder has all 4 PNG files

**Issue: Auto-monitor doesn't work**
- **Cause:** Content script not loaded or permission issue
- **Solution:**
  1. Check chrome://extensions/ for errors
  2. Reload extension
  3. Refresh xiaohongshu.com page
- **Verify:** Console should show "[自动监控] 已启动"

**Issue: No data captured**
- **Cause:** Page structure changed or wrong page type
- **Solution:**
  1. Check console for errors
  2. Verify on correct page (xiaohongshu.com)
  3. Check if selectors need updating
- **Verify:** Console should show "[自动抓取]" messages

**Issue: CSV export has garbled text**
- **Cause:** Encoding issue when opening CSV
- **Solution:** Open CSV in Excel and select UTF-8 encoding
- **Verify:** Chinese characters display correctly

**Issue: Extension disabled after Chrome restart**
- **Cause:** Developer mode extensions show warnings
- **Solution:** This is normal for unpacked extensions
- **Note:** Published extensions don't have this issue

### Debug Logging

**Enable verbose logging:**
```javascript
// In content.js, all logs prefixed with:
console.log('[自动监控]', message);
console.log('[自动抓取]', message);
console.log('[详情页抓取]', message);

// In background.js:
console.log('[后台]', message);

// Watch console (F12) for these messages
```

**Check extension errors:**
```
chrome://extensions/ → Extension card → "错误" or "Errors" link
```

---

## Development Best Practices

### Before Making Changes

1. **Read existing code** - Understand current implementation
2. **Check console logs** - See what's happening in real-time
3. **Test on real site** - Use actual xiaohongshu.com pages
4. **Review CLAUDE.md** - Check if similar changes documented

### While Coding

1. **Use console.log liberally** - Debug extraction logic
2. **Test incrementally** - Don't change multiple things at once
3. **Preserve fallback strategies** - Keep robustness
4. **Comment complex logic** - Explain non-obvious code

### After Changes

1. **Reload extension** - chrome://extensions/ → Reload
2. **Test all modes** - Auto-monitor + manual capture
3. **Check console** - Look for errors or warnings
4. **Test CSV export** - Verify data integrity
5. **Update CLAUDE.md** - Document significant changes

### Before Distribution

1. **Update version** - Increment in manifest.json
2. **Test package** - Extract and test from ZIP
3. **Review documentation** - Update user-facing docs
4. **Run package.sh** - Create distribution ZIP

---

## Chrome Web Store Submission Checklist

### Prerequisites
- [x] Extension fully tested and working
- [x] manifest.json author field filled
- [x] Icons created (all 4 sizes)
- [x] Privacy policy prepared
- [ ] Privacy policy hosted online (pending)
- [ ] Screenshots created (pending)
- [ ] Promotional tile created (pending)
- [ ] Developer account registered (pending)

### Submission Steps
1. Register at https://chrome.google.com/webstore/devconsole
2. Pay $5 developer registration fee
3. Upload xiaohongshu-crawler-v3.0.zip
4. Fill store listing (use STORE_LISTING.md content)
5. Upload screenshots and promotional materials
6. Enter privacy policy URL
7. Fill permission justifications
8. Submit for review (typically 1-3 days)

### Reference Documents
- **Chrome商店上架实操指南.md** - Complete submission guide
- **上架清单.md** - Quick checklist
- **STORE_LISTING.md** - Pre-written store listing content
- **PRIVACY_POLICY.md** - Privacy policy text

---

## Contact & Support

**For development questions:**
- Review this CLAUDE.md file
- Check console logs for debugging
- Inspect xiaohongshu.com page structure (F12)

**For testing:**
- Use test-extension/ folder
- Follow 测试指南.md
- Fill out 测试结果反馈表.md

**For distribution:**
- Use xiaohongshu-crawler-测试版.zip
- Reference 分发测试指南.md
- Collect feedback via 测试反馈表.txt

---

## Quick Command Reference

```bash
# Development
open icons/icon-generator.html          # Generate icons
code .                                  # Open in VS Code

# Packaging
./package.sh                            # Create distribution ZIP

# Testing
open -R xiaohongshu-crawler-v3.0.zip   # Show extension package
open -R "xiaohongshu-crawler-测试版.zip" # Show distribution package

# Chrome URLs
chrome://extensions/                    # Extension management
chrome://version/                       # Chrome version info
```

---

**This project is ready for distribution testing and Chrome Web Store submission.**

**Next recommended action:**
- Send distribution package to test users, OR
- Create screenshots and submit to Chrome Web Store

For questions or issues, refer to the relevant documentation files listed above.
