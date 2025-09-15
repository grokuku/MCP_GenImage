#### Fichier : features.md
# MCP_GenImage Features

This document outlines the tools provided by the MCP_GenImage server.

---

## Tool: `generate_image`

Generates an image based on a textual description by processing it through a ComfyUI workflow. The process includes applying predefined styles and optional LLM-based prompt enhancement.

### Parameters

| Name              | Type           | Required | Default | Description                                                                                                                              |
|-------------------|----------------|----------|---------|------------------------------------------------------------------------------------------------------------------------------------------|
| `prompt`          | `string`       | Yes      | -       | A detailed textual description of the desired image.                                                                                     |
| `negative_prompt` | `string`       | No       | `""`    | A description of elements to avoid in the image (e.g., "ugly, deformed, bad anatomy").                                                   |
| `style_names`     | `array[string]`| No       | `[]`    | A list of style names to apply (e.g., `["Cinematic", "Photorealistic"]`). Styles are configured in the web UI.                               |
| `aspect_ratio`    | `string`       | No       | `null`  | The desired aspect ratio. Supported values: `"1:1"`, `"16:9"`, `"9:16"`, `"4:3"`, `"3:4"`. Defaults to the workflow's setting. |
| `render_type`     | `string`       | No       | `null`  | The specific render workflow to use (e.g., `UPSCALE_4X`). Overrides the default. Render Types are configured in the web UI.               |
| `enhance_prompt`  | `boolean`      | No       | `true`  | If true, an LLM (Ollama) will be used to enhance the prompts before generation. Requires Ollama to be configured in the web UI.               |

### Output

Returns a JSON object containing the URL of the generated image, within the standard MCP `content` structure.

**Example Structure:**
```json
{
    "content": {
        "type": "image",
        "source": "http://your_public_url:8001/outputs/ComfyUI_00001_.png"
    }
}
```

---