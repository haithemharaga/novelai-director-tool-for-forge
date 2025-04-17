import gradio as gr
import modules.scripts as scripts
from modules import shared, processing
from modules.ui_components import ToolButton
from PIL import Image
import requests
import json
import base64
import io
import traceback # For detailed error logging

# --- Configuration ---
# !!! VERY IMPORTANT: Verify this endpoint. It might change. !!!
NAI_API_ENDPOINT = "https://api.novelai.net/ai/generate-image"
# Default NAI sampler names (Verify these are correct for the API!)
NAI_SAMPLERS = [
    "k_euler", "k_euler_ancestral", "k_dpmpp_2s_ancestral",
    "k_dpmpp_sde", "ddim_v3" # Add/remove based on NAI API docs/observation
]

# --- API Call Helper ---
def call_novelai_api(api_key, prompt, neg_prompt, width, height, steps, scale, sampler, seed, director_json_str):
    """
    Handles the construction of the request and the call to the NovelAI API.
    Returns: Tuple (list[PIL.Image] | None, str) -> (images, info_text/error_message)
    """
    if not api_key:
        return None, "Error: NovelAI API Key is missing."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "accept": "application/json" # Often required by APIs
    }

    # --- Parse Director Tools JSON ---
    director_params = {}
    if director_json_str and director_json_str.strip():
        try:
            director_params = json.loads(director_json_str)
            if not isinstance(director_params, dict):
                 raise ValueError("Director Tools JSON must decode to a dictionary (object).")
        except json.JSONDecodeError as e:
            return None, f"Error: Invalid JSON in Director Tools field: {e}"
        except ValueError as e:
             return None, f"Error: {e}"

    # --- Construct API Payload ---
    # !!! CRITICAL: This payload structure is SPECULATIVE based on common patterns
    # !!!          and needs verification against the actual NovelAI API.
    # !!!          Director Tools parameters ('director_settings' below) are a GUESS.
    payload = {
        "input": prompt,
        "model": "nai-diffusion-3", # Or make selectable in UI
        "action": "generate",       # Check if required/correct
        "parameters": {
            "negative_prompt": neg_prompt,
            "width": width,
            "height": height,
            "steps": int(steps),
            "scale": float(scale),
            "sampler": sampler,     # Ensure this name matches NAI's expectation
            "seed": int(seed),
            "qualityToggle": True,  # Example potential NAI param
            "ucPreset": 0,          # Example potential NAI param (UC Preset)
            # Add other NAI specific parameters found through observation
            # --- Integrate Director Tools Parameters ---
            # **director_params # Simple merge - assumes director_json_str contains keys for the 'parameters' object
            # OR maybe it's a specific key like this (PURE GUESS):
            # "director_guidance": director_params
            # --->>> YOU MUST DETERMINE THE CORRECT STRUCTURE HERE <<<---
        }
    }

    # If director params were loaded and are non-empty, try merging them
    # Adjust this logic based on where director tools actually go in the payload
    if director_params:
        payload['parameters'].update(director_params) # Example: Merging into 'parameters'

    # Log the request payload for debugging (Remove API key if logging publicly)
    log_payload = json.loads(json.dumps(payload)) # Deep copy for logging
    # Consider removing sensitive data for logs: log_payload.pop('input', None) ?
    info_text = f"NovelAI Request Payload (Check Console for Full Details)" # Placeholder
    print("--- Sending Payload to NovelAI ---")
    print(json.dumps(log_payload, indent=2))
    print("---------------------------------")


    try:
        response = requests.post(NAI_API_ENDPOINT, headers=headers, json=payload, timeout=180) # Long timeout for generation

        print(f"NovelAI Response Status Code: {response.status_code}")
        # print(f"NovelAI Response Headers: {response.headers}") # For debugging NAI headers (cost, seed etc.)
        # print(f"NovelAI Response Body (text): {response.text[:500]}...") # Log beginning of response

        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        # --- Process NAI Response ---
        # !!! CRITICAL: This response handling is SPECULATIVE. NAI might return:
        # !!! 1. Zipped file containing image(s) and metadata.
        # !!! 2. JSON with base64 encoded image(s).
        # !!! 3. Server-Sent Events stream.
        # !!! -> You MUST inspect the actual response to implement this correctly. <-

        # Example: Assuming response is like the event stream with base64 data
        content_type = response.headers.get('content-type', '')
        if 'application/zip' in content_type:
            # Handle zip file (needs zipfile module)
            return None, "Error: Zip response handling not implemented yet."
            # import zipfile
            # with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            #     # find image files, extract, open with PIL...
        elif 'text/event-stream' in content_type or response.text.strip().startswith('event:'):
             # Example parsing for event stream like structure (VERY FRAGILE)
            lines = response.text.strip().split('\n')
            b64_data = None
            for line in lines:
                if line.startswith('data:'):
                    b64_data = line[len('data:'):].strip()
                    break # Assume first data line has the image
            if not b64_data:
                print(f"Could not find base64 data in event-stream response:\n{response.text}")
                return None, f"Error: Could not parse image data from NovelAI stream. Status: {response.status_code}"

            try:
                img_data = base64.b64decode(b64_data)
                image = Image.open(io.BytesIO(img_data))
                print("Image received and decoded from event stream.")
                # Try to extract NAI cost/seed from headers if available
                # final_info = f"NovelAI Info:\nSeed: {response.headers.get('actual-seed', seed)}\nCost: {response.headers.get('anlas-cost', 'N/A')}"
                final_info = f"Successfully generated image via NovelAI.\nSeed: {seed} (API might use/return a different one)\n(Check console logs for request details)"
                return [image], final_info # Return list of images and info string
            except Exception as decode_err:
                 print(f"Error decoding base64 data: {decode_err}")
                 return None, f"Error decoding image data from NovelAI: {decode_err}"

        elif 'application/json' in content_type:
             # Handle JSON response (assuming base64 data inside)
             try:
                 json_response = response.json()
                 # GUESS structure: json_response['images'][0] ? json_response['output']?
                 # b64_data = json_response['some_key_with_base64']
                 return None, "Error: JSON response handling not implemented yet (unknown structure)."
             except json.JSONDecodeError:
                 return None, f"Error: Failed to decode JSON response. Status: {response.status_code}, Content: {response.text[:200]}"

        else:
             # Fallback/Unknown content type
             return None, f"Error: Unexpected Content-Type from NovelAI: {content_type}. Status: {response.status_code}"


    except requests.exceptions.Timeout:
        print("NovelAI request timed out.")
        return None, "Error: Request to NovelAI timed out."
    except requests.exceptions.HTTPError as e:
         # Handle HTTP errors (like 401 Unauthorized, 400 Bad Request, 500 Server Error)
        error_details = f"HTTP Error: {e.response.status_code}"
        try:
            # Try to get error message from NAI response body
            nai_error = e.response.json() # Assuming error details are in JSON
            error_details += f"\nNovelAI Message: {nai_error.get('message', e.response.text)}"
        except:
            error_details += f"\nResponse: {e.response.text[:200]}" # Fallback to raw text
        print(f"NovelAI API HTTP Error: {error_details}")
        return None, f"NovelAI API Error: {error_details}"
    except requests.exceptions.RequestException as e:
        print(f"Network error calling NovelAI API: {e}")
        return None, f"Error: Network error connecting to NovelAI API: {e}"
    except Exception as e:
        # Catch-all for unexpected errors during processing
        print(f"!!! Unexpected Error in call_novelai_api !!!")
        print(traceback.format_exc())
        return None, f"Unexpected Error: {e}"


# --- Gradio UI Script ---
class NovelAIDirectorScript(scripts.Script):

    def title(self):
        return "NovelAI Director Tools Integration"

    def show(self, is_img2img):
        # Show in txt2img, hide in img2img (or vice versa, or always visible)
        return scripts.AlwaysVisible # Or: return not is_img2img

    def ui(self, is_img2img):
        # Use accordion for better layout in the scripts section
        with gr.Accordion(self.title(), open=False):
            enabled = gr.Checkbox(label="Override with NovelAI Generation", value=False,
                                  info="If checked, generation will use NAI API instead of local model.")
            api_key = gr.Textbox(label="NovelAI API Key", type="password",
                                 placeholder="Enter your NovelAI API key (Bearer token)",
                                 info="Requires NAI subscription with API access (e.g., Opus). Handled securely in browser, sent directly to NAI.")

            # NAI specific parameters (mirroring common SD params)
            with gr.Row():
                steps = gr.Slider(minimum=1, maximum=100, step=1, value=28, label="NAI Steps")
                sampler = gr.Dropdown(NAI_SAMPLERS, value="k_euler_ancestral", label="NAI Sampler", # Default to a common NAI sampler
                                       info="Ensure sampler name matches exactly what NAI API expects.")
            with gr.Row():
                scale = gr.Slider(minimum=0.0, maximum=20.0, step=0.1, value=6.0, label="NAI CFG Scale", # NAI often uses slightly different defaults
                                  info="NovelAI's guidance scale.")
                seed = gr.Number(label="NAI Seed", value=-1, precision=0,
                                 info="-1 for random. NAI might return the actual seed used.")

            # --- Director Tools Input ---
            # This is the most basic input method. A better UI would require more complex Gradio/HTML.
            director_tools_json = gr.Textbox(
                label="Director Tools (JSON format)",
                placeholder='Enter Director Tools parameters as a valid JSON object.\nExample (!! STRUCTURE IS A GUESS !!):\n{\n  "qualityToggle": true,\n  "ucPreset": 0,\n  "attention_shift": [{"phrase": "red hair", "strength": 1.5}]\n}',
                lines=6,
                info="ADVANCED: Requires knowing the exact JSON structure NAI expects for Director features."
            )

            # Add info text about costs and API usage
            gr.Markdown("""
            **Warning:** Using this feature sends your prompts and settings to NovelAI's servers via their **unofficial API**.
            - Requires an active NovelAI subscription tier with API access (e.g., Opus).
            - API usage consumes **Anlas**. Check your NAI account for costs.
            - The NovelAI API is subject to change without notice, which may break this extension.
            - Ensure compliance with NovelAI's Terms of Service.
            """)

        # Return the list of Gradio components that script settings are derived from
        # The order MUST match the order of arguments in the run() method (after `p`)
        return [enabled, api_key, steps, sampler, scale, seed, director_tools_json]

    # This method is called by the WebUI processing pipeline
    def run(self, p: processing.StableDiffusionProcessing, enabled, api_key, steps, sampler, scale, seed, director_tools_json):
        """
        p: The processing object containing standard SD parameters (prompt, neg_prompt, width, height, etc.)
        The rest are the values from the UI components returned by ui()
        """

        if not enabled:
            # If not enabled, do nothing and let the standard pipeline continue
            print("NovelAI script: Disabled, skipping.")
            return processing.Processed(p, [], p.seed, "") # Must return a Processed object

        print("NovelAI script: Enabled, attempting to override generation.")

        # Use parameters from the main UI (prompt, negative_prompt, width, height)
        # Use parameters from our script's UI (steps, sampler, scale, seed, api_key, director_json)
        images, info_text = call_novelai_api(
            api_key=api_key,
            prompt=p.prompt,
            neg_prompt=p.negative_prompt,
            width=p.width,
            height=p.height,
            steps=steps,
            scale=scale,
            sampler=sampler,
            seed=seed,
            director_json_str=director_tools_json
        )

        if images:
            print(f"NovelAI script: Successfully received {len(images)} image(s).")
            # Create a Processed object to return results to the WebUI
            # Use the seed requested, as the actual seed might not be easily available/parsed yet
            # The info_text from call_novelai_api will be displayed in the UI
            proc = processing.Processed(p, images, int(seed), info_text)

            # Optional: Try to update the 'infotexts' field with more structured data if needed by other extensions
            # proc.infotexts = [info_text] * len(images)

            return proc
        else:
            # If the API call failed, info_text contains the error message
            print(f"NovelAI script: API call failed. Error: {info_text}")
            # Return an empty Processed object but include the error message in the info field
            # This prevents the WebUI from potentially crashing and shows the error to the user
            p.extra_generation_params["NovelAI Error"] = info_text # Add to extra params
            return processing.Processed(p, [], p.seed, f"NovelAI Generation Failed: {info_text}")

