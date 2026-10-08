# Cinematic Frame — Render + Custom GPT Action

This is a working first version for exact sizing and real logo compositing. It does **not** automatically identify movies on the server, search logo databases, or perform AI outpainting. Your GPT identifies the movie and finds a supported logo, or requests a logo upload. The complete frame remains visible below deliberate solid dark negative space. This is not yet the seamless cinematic extension in your original brief.

## Deploy
1. Create a GitHub account/repository if needed. Upload the contents of this folder into the repository root (not the ZIP itself). Do not upload secrets.
2. In Render: New > Blueprint; connect this repository. The included render.yaml configures the service. Free hosting can sleep; open /health and wait before testing an Action.
3. In Render > service > Environment, retrieve ACTION_API_KEY. Keep it secret. This is your own service key, not an OpenAI key.
4. Copy the service HTTPS address, e.g. https://cinematic-frame-xxxx.onrender.com.
5. In action-schema.json replace https://YOUR-SERVICE.onrender.com with that real address.
6. Custom GPT > Configure > Actions > Create new action. Paste action-schema.json. Authentication: API Key, Bearer; use ACTION_API_KEY. Paste gpt-instructions.txt into GPT Instructions. Enable web search.
7. Test with a movie frame plus its transparent title logo. The response must report width 2000, height 2800, and give an accessible poster_url. Check the downloaded image dimensions.

## Limits
- Transparent logo PNG/WebP is required. SVG is unsupported. Logos keep their supplied colors; no automatic recoloring/gradient yet.
- Downloads are restricted to image.tmdb.org and *.oaiusercontent.com. If ChatGPT supplies another host, this version will reject it; diagnose the actual host before extending the allowlist.
- PNG results live temporarily in memory for at most one hour and disappear on restart/sleep. Download promptly. Durable storage is needed before production use.
- Bearer API authentication protects rendering. Output links contain random tokens; anyone with a link can view that output until expiry.
- Requires no OpenAI API key because there is no server-side image generation. AI outpainting later requires a separate provider and budget.
- No guarantee that your GPT can find a transparent original logo for every film. Missing logo results in an error, never a logo-free 'finished' poster.

This package is prepared for deployment; it has not been deployed into your account or tested end-to-end with a live Custom GPT.
