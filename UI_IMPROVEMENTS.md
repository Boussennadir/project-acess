# UI Color Theme Update — Orange & Gray

## Overview
Your PyQt6 application has been redesigned with a modern **orange and gray** color palette, replacing the previous teal/blue theme. The new design is more sophisticated, warm, and professional.

---

## Color Palette Changes

### Previous Theme (Teal/Blue)
```
Background:     #0a0e1a (very dark blue)
Secondary BG:   #111827 (dark blue)
Tertiary BG:    #1a2236 (blue-gray)
Border:         #1e3a5f (dark blue)
Primary Color:  #00c9b1 (teal)
Accent:         #00796b (darker teal)
Text:           #e2eaf8 (light blue)
```

### New Theme (Orange & Gray)
```
Background:     #0f0f0f (pure black)
Secondary BG:   #1a1a1a (dark gray)
Tertiary BG:    #252525 (medium-dark gray)
Border:         #3a3a3a (lighter gray)
Primary Color:  #ff8c42 (vibrant orange)
Accent:         #d96d2e (darker orange)
Text:           #f5f5f5 (clean white)
Text Secondary: #a0a0a0 (light gray)
```

---

## What Changed

### 1. **Sidebar Navigation**
- Logo color: Teal → **Orange**
- Navigation hover effect: Teal → **Orange**
- Active nav indicator: Teal → **Orange**
- Border color: Dark teal → **Dark orange**

### 2. **Input Fields & Dropdowns**
- Focus border color: Teal → **Orange**
- Focus background: #1e2d45 → **#2a2520** (warmer tone)
- Dropdown selection: Teal → **Orange**

### 3. **Cards & Sections**
- Top border accent: Teal → **Orange**
- Card borders: Teal → **Orange**

### 4. **Buttons**
- Primary button border: Teal → **Orange**
- Primary button hover background: Teal → **Orange**
- Primary button text: Teal → **Orange**

### 5. **Tables**
- Header text color: Teal → **Orange**
- Header border: Teal → **Orange**
- Selected row highlight: Teal → **Orange**

### 6. **Tabs & Labels**
- Tab indicator: Teal → **Orange**
- Field labels: Teal → **Orange**

### 7. **Other UI Elements**
- Scrollbar handle: Teal → **Orange**
- Message box buttons: Teal → **Orange**
- Section headers: Teal → **Orange**

---

## Status Color Meanings (Unchanged)
- **Pending**: Orange `#ff8c42` (still orange, now matches primary theme!)
- **Active**: Green `#66bb6a`
- **Suspended**: Red `#e74c3c`
- **Inactive**: Gray `#a0a0a0`
- **Archived**: Dark gray `#505050`

---

## Category Colors (Updated)
- **STU (Students)**: Orange `#ff8c42`
- **FAC (Faculty)**: Green `#66bb6a`
- **STF (Staff)**: Orange `#ff8c42`
- **EXT (External)**: Purple `#9b59b6`

---

## Benefits of This Design

✅ **Warmer aesthetic** - Orange creates a welcoming, energetic feeling  
✅ **Better contrast** - Cleaner grays with vibrant orange creates excellent readability  
✅ **Professional look** - Orange + gray is a popular enterprise design choice  
✅ **Improved consistency** - The "Pending" status now aligns with the primary brand color  
✅ **Modern feel** - Pure blacks and clean whites feel contemporary  

---

## How to Use

1. Replace your `app.py` with the updated version
2. Keep `utils.py` and `db.py` as they are (no changes needed)
3. Run: `python3 app.py`
4. Database connections and functionality remain unchanged

---

## If You Want to Adjust Colors Further

All colors are defined at the top of `app.py` (lines 32-37). You can easily customize:

```python
BG="#0f0f0f"           # Main background
BG2="#1a1a1a"          # Secondary background
BG3="#252525"          # Tertiary background
BORDER="#3a3a3a"       # Border color
TEXT="#f5f5f5"         # Main text
TEXT2="#a0a0a0"        # Secondary text
ORANGE="#ff8c42"       # Primary accent (change this to any color!)
ORANGE_DIM="#d96d2e"   # Darker variant
GREEN="#66bb6a"        # Success/Active state
RED="#e74c3c"          # Error/Suspended state
PURPLE="#9b59b6"       # External category
```

---

## Files Updated
- ✅ **app.py** - Complete UI theme redesign
- ✅ **utils.py** - No changes needed
- ✅ **db.py** - No changes needed

Enjoy your new modern orange & gray interface! 🎨
