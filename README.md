```markdown
# NovelAI Director Tools Integration for Stable Diffusion Web UI (Forge/A1111)

**WARNING: Highly Experimental & Uses Unofficial API**

This extension attempts to integrate with the NovelAI API to allow using their generation capabilities, potentially including Director Tools features, directly from the Stable Diffusion Web UI.

## Features (Attempted)

*   Overrides local SD generation with a call to the NovelAI API when enabled.
*   UI elements for NovelAI API Key and common generation parameters.
*   Basic JSON input field for specifying NovelAI Director Tools parameters (Requires knowledge of the **undocumented** NAI API structure).

## Disclaimer & Warnings

*   **Unofficial API:** This extension uses NovelAI's **internal/undocumented API**. It is **not officially supported** by NovelAI.
*   **Terms of Service:** Using this API might violate NovelAI's Terms of Service. Use at your own risk.
*   **API Changes:** The NovelAI API can change **at any time without warning**, which will likely break this extension.
*   **Cost (Anlas):** API usage requires a NovelAI subscription tier granting API access (e.g., Opus) and **consumes Anlas credits**. Monitor your usage on the NovelAI website.
*   **Security:** Your NovelAI API key is required. While handled client-side by Gradio/browser for input, be cautious about where you use this extension.
*   **Director Tools Structure:** The exact JSON structure needed for Director Tools is **unknown** and must be determined through reverse-engineering or community findings. The current JSON input is a placeholder.
*   **Response Parsing:** Handling the response from NovelAI (image data, metadata) is based on assumptions and may need adjustments.

## Installation

1.  Clone or download this repository/folder.
2.  Place the `sd-webui-novelai-director` folder inside the `extensions/` directory of your Stable Diffusion Web UI (Forge/A1111) installation.
3.  **Restart** the Stable Diffusion Web UI.
4.  The extension might automatically attempt to install the `requests` library if missing (check the console on startup). If not, you might need to manually install it in your Web UI's Python environment:
    ```bash
    # Activate your webui's python environment first (e.g., venv/Scripts/activate or conda activate)
    pip install -r extensions/sd-webui-novelai-director/requirements.txt
    ```

## Usage

1.  Go to the `txt2img` or `img2img` tab in the Web UI.
2.  Scroll down to the `Scripts` dropdown at the bottom.
3.  Select `"NovelAI Director Tools Integration"` from the list.
4.  An accordion menu with the extension's settings will appear.
5.  Check the `Override with NovelAI Generation` checkbox to enable it.
6.  Enter your NovelAI API Key (the Bearer token).
7.  Configure the NAI-specific Steps, Sampler, CFG Scale, and Seed.
8.  (Advanced) If you know the required JSON structure, enter the Director Tools parameters in the JSON text box.
9.  Configure your main Prompt, Negative Prompt, Width, Height, etc., in the standard Web UI fields.
10. Click the main `Generate` button. If enabled, the extension will intercept the process and call the NovelAI API instead of using your local model.
11. The results (or errors) from NovelAI should appear in the output gallery. Check the console/terminal running the Web UI for detailed logs and potential errors."# novelai-director-tool-for-forge" 
