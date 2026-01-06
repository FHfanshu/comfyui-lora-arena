import logging
import os
import torch
import kgen.models as models
import kgen.executor.tipo as tipo
from kgen.formatter import seperate_tags, apply_format

logger = logging.getLogger(__name__)

DEFAULT_FORMAT = """<|special|>, <|characters|>, <|copyrights|>,
<|artist|>,

<|extended|>.

<|general|>,

<|generated|>.

<|quality|>, <|meta|>, <|rating|>
"""

class PromptService:
    _instance = None
    _model_loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PromptService, cls).__new__(cls)
        return cls._instance

    def _ensure_model_loaded(self):
        if not self._model_loaded:
            logger.info("Loading TIPO-500M model...")
            try:
                from config import get_config
                from pathlib import Path
                config = get_config()

                # Set HuggingFace cache directory to models folder
                models_cache_dir = config.get("models_cache_dir")
                if models_cache_dir:
                    cache_path = Path(models_cache_dir)
                    cache_path.mkdir(parents=True, exist_ok=True)
                    os.environ["HF_HOME"] = str(cache_path)
                    os.environ["HUGGINGFACE_HUB_CACHE"] = str(cache_path / "hub")
                    logger.info(f"Model cache directory set to: {models_cache_dir}")

                device = "cuda" if torch.cuda.is_available() else "cpu"
                model_repo = config.get("tipo_model_repo", "KBlueLeaf/TIPO-500M")
                gguf_name = config.get("tipo_gguf_filename", "TIPO-500M_epoch5-F16.gguf")
                use_gguf = config.get("tipo_use_gguf", True)

                if use_gguf:
                    if getattr(models, "Llama", None) is None:
                        raise RuntimeError(
                            "TIPO GGUF model requires llama-cpp-python. Install it or disable GGUF mode."
                        )
                    model_file = models.download_gguf(model_repo, gguf_name)
                    models.load_model(
                        str(model_file),
                        device=device,
                        gguf=True,
                    )
                else:
                    models.load_model(
                        model_repo,
                        device=device,
                        gguf=False
                    )
                self._model_loaded = True
                logger.info(f"TIPO-500M model loaded successfully on {device}")
            except Exception as e:
                logger.error(f"Failed to load TIPO model: {e}")
                raise

    def optimize_prompt(self, user_prompt: str, tag_length: str = "long") -> str:
        self._ensure_model_loaded()

        try:
            # Parse user input as initial tags
            # Split by comma and clean up
            input_tags = [tag.strip() for tag in user_prompt.split(",") if tag.strip()]
            tag_map = seperate_tags(input_tags)

            meta, operations, general, nl_prompt = tipo.parse_tipo_request(
                tag_map=tag_map,
                nl_prompt="",  # No natural language input
                tag_length_target=tag_length,
                expand_tags=True,
                expand_prompt=False,  # Don't generate NL description
                generate_extra_nl_prompt=False,  # Don't generate extra NL
            )

            result, timing = tipo.tipo_runner(meta, operations, general, nl_prompt)

            # Extract only tags, not NL description
            # result is a tag_map dict, we need to flatten it to comma-separated tags
            all_tags = []
            for category in ['special', 'characters', 'copyrights', 'artist', 'general', 'meta', 'quality', 'rating']:
                if category in result and result[category]:
                    all_tags.extend(result[category])

            optimized = ", ".join(all_tags)

            return optimized
        except Exception as e:
            logger.error(f"Error optimizing prompt: {e}")
            return user_prompt # Fallback to original prompt

prompt_service = PromptService()
