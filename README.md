# Map the Field 2026

A structured exploration of the tech × social impact job market using an LLM-maintained wiki published as a static site.

## Quick Start

### Prerequisites

- **Node.js 22+** and **npm 10.9.2+**

If you need to upgrade on Ubuntu:
```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 22
nvm use 22
```

### Installation

1. **Clone and install Quartz:**
   ```bash
   git clone https://github.com/jackyzha0/quartz.git
   cd quartz
   npm install
   ```

2. **Set up content structure:**
   ```bash
   cd ..
   mkdir -p content/{wiki,articles,sources}
   cd quartz
   ln -s ../content content
   cd ..
   ```

3. **Start the dev server:**
   ```bash
   cd quartz
   npx quartz build --serve
   ```

   Open `http://localhost:8080` in your browser.

## File Structure

```
map_the_field_2026/
├── quartz/                 # Quartz SSG (static site generator)
│   ├── quartz.config.ts    # Site configuration
│   ├── content -> ../content (symlink)
│   └── public/             # Built static site
├── content/                # Your actual content (markdown)
│   ├── wiki/               # LLM-maintained knowledge base
│   ├── articles/           # Refined, narrative pieces
│   ├── sources/            # Index of ingested documents
│   ├── index.md            # Home page
│   └── log.md              # Project timeline
├── raw_source/             # Raw ingested documents (not published)
├── CLAUDE.md               # Project instructions for Claude
└── README.md
```

## Configuration

**Quartz config** (`quartz/quartz.config.ts`):
- `pageTitle`: "Map the Field 2026"
- `baseUrl`: `localhost:3000` (for local development; change for deployment)
- `analytics`: disabled for personal projects
- `ignorePatterns`: includes `raw_source` so raw documents don't appear on the site

The Quartz config is already set up. Only edit it if you want to customize colors, fonts, or add new plugins.

## Development

After editing content files, the site auto-rebuilds. Just refresh your browser to see changes. To start the dev server:

```bash
cd quartz
npx quartz build --serve
```

## Publishing

To build a production version:
```bash
cd quartz
npx quartz build
```

The static site is in `quartz/public/`. Deploy this directory to any static host (Netlify, GitHub Pages, Vercel, etc.).
