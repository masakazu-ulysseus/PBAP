# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PBAP (PANZER BLOCKS Assist Parts) is a web application for users to request missing parts for PANZER BLOCKS products. The system consists of two separate applications:

1. **User System** (Next.js - Not yet implemented): Public-facing part request form
2. **Admin Tool** (Python/Streamlit - `apps/admin-tool/`): Internal management tool for:
   - Task management (incoming part requests)
   - Product/image registration with automated image processing

## Tech Stack

### Admin Tool (Python)
- **Framework**: Streamlit 1.28.0
- **Image Processing**: OpenCV (headless), Pillow, NumPy
- **Backend**: Supabase (PostgreSQL + Storage)
- **Key Libraries**: `streamlit-image-coordinates` for interactive image selection

### User System (Planned)
- **Framework**: Next.js (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS

## Development Commands

### Admin Tool

```bash
# Navigate to admin tool
cd apps/admin-tool

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Streamlit app
streamlit run src/main.py

# Run tests
pytest src/tests/

# Run single test file
pytest src/tests/test_image_processing.py -v
```

### Database

```bash
# Apply schema to Supabase (via SQL Editor in Supabase dashboard)
# Schema file: supabase/schema.sql
```

## Environment Configuration

Create `.env` file in `apps/admin-tool/`:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
```

## Architecture

### Data Model (PostgreSQL)
```
Products → AssemblyPages → AssemblyImages → Parts
                                    ↓
                           AssemblyImageParts (junction)

Tasks → TaskDetails → Parts
```

- **Products**: Product master data (name, series, country)
- **AssemblyPages**: Assembly instruction pages (large images)
- **AssemblyImages**: Individual assembly number regions (medium images)
- **Parts**: Individual part images (small images)
- **Tasks**: User part requests
- **TaskDetails**: Specific parts requested per task

### Image Processing Pipeline

Located in `apps/admin-tool/src/utils/image_processing.py`:

1. **NumberExtractor**: Detects assembly numbers using color-based feature matching (HSV)
2. **Part Extraction Flow**:
   - Detect largest rectangular frame in image
   - Super-resolution (2x upscale with INTER_CUBIC)
   - Sharpening (unsharp mask)
   - Noise reduction (median filter, kernel=7)
   - Contour detection with area/aspect ratio filtering
   - Object count validation (exclude multi-object regions)

### Admin Tool Structure

```
apps/admin-tool/src/
├── main.py              # Entry point, page routing
├── pages/
│   ├── product_list.py       # Product listing with search/filter
│   └── product_registration.py  # Multi-step product registration workflow
├── utils/
│   ├── image_processing.py   # OpenCV-based image analysis
│   └── supabase_client.py    # Supabase client singleton
└── tests/
    ├── test_image_processing.py
    └── test_supabase_client.py
```

### Product Registration Workflow

1. Enter product info (name, series, country)
2. Upload assembly page image
3. Click to select assembly number regions (2-point rectangle selection)
4. Enter assembly number for each region
5. Auto-extract parts from each assembly image
6. Save all data to Supabase (Products → Pages → Images → Parts)

## Key Technical Decisions

- Images are converted to WebP and resized (max 2000px) before upload
- Supabase Storage bucket: `product-images` (public)
- RLS policies allow public read, but write operations currently use anon key (to be secured later)
- Assembly number detection uses HSV color space for black/red text discrimination
- Part extraction filters: min area 2000px, aspect ratio 0.2-5.0, single significant object per contour

## POC Directory

`poc/` contains proof-of-concept scripts for image processing algorithms:
- `extract_numbers.py`: Assembly number detection experiments
- `extract_parts.py`: Part extraction experiments
- Various analysis reports documenting algorithm iterations
