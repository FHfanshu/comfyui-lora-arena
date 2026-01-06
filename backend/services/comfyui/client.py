"""
ComfyUI API Client

Handles communication with ComfyUI server for image generation.
"""

import aiohttp
import asyncio
import json
import uuid
from typing import Optional, Callable, Dict, Any, List, Tuple
from pathlib import Path


class ComfyUIClient:
    """Async client for ComfyUI API"""

    def __init__(self, base_url: str = "http://localhost:8188"):
        self.base_url = base_url.rstrip("/")
        self.client_id = str(uuid.uuid4())

    @property
    def ws_url(self) -> str:
        """Get WebSocket URL from base URL"""
        if self.base_url.startswith("https://"):
            return f"wss://{self.base_url[8:]}/ws"
        else:
            return f"ws://{self.base_url[7:]}/ws"

    async def check_connection(self) -> bool:
        """Check if ComfyUI server is available"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/system_stats",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except Exception:
            return False

    async def get_system_stats(self) -> Dict[str, Any]:
        """Get ComfyUI system statistics"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/system_stats") as response:
                return await response.json()

    async def get_object_info(self, node_class: str = None) -> Dict[str, Any]:
        """Get node object info (for available options)"""
        url = f"{self.base_url}/object_info"
        if node_class:
            url += f"/{node_class}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()

    async def get_available_checkpoints(self) -> List[str]:
        """Get list of available checkpoint models"""
        try:
            info = await self.get_object_info("CheckpointLoaderSimple")
            return info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
        except Exception:
            return []

    async def get_available_loras(self) -> List[str]:
        """Get list of available LoRA models"""
        try:
            info = await self.get_object_info("LoraLoader")
            return info["LoraLoader"]["input"]["required"]["lora_name"][0]
        except Exception:
            return []

    async def get_available_samplers(self) -> List[str]:
        """Get list of available samplers"""
        try:
            info = await self.get_object_info("KSampler")
            return info["KSampler"]["input"]["required"]["sampler_name"][0]
        except Exception:
            return ["euler", "euler_ancestral", "dpmpp_2m", "dpmpp_sde"]

    async def queue_prompt(self, workflow: Dict[str, Any]) -> str:
        """
        Submit a workflow to ComfyUI queue.

        Args:
            workflow: ComfyUI workflow JSON

        Returns:
            prompt_id for tracking
        """
        payload = {
            "prompt": workflow,
            "client_id": self.client_id
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/prompt",
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to queue prompt: {error_text}")
                result = await response.json()
                return result["prompt_id"]

    async def get_history(self, prompt_id: str) -> Dict[str, Any]:
        """Get generation history for a prompt"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/history/{prompt_id}") as response:
                data = await response.json()
                return data.get(prompt_id, {})

    async def get_image(
        self,
        filename: str,
        subfolder: str = "",
        folder_type: str = "output"
    ) -> bytes:
        """
        Get a generated image from ComfyUI.

        Args:
            filename: Image filename
            subfolder: Subfolder within output directory
            folder_type: Folder type (output, input, temp)

        Returns:
            Image bytes
        """
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/view",
                params=params
            ) as response:
                if response.status != 200:
                    raise Exception(f"Failed to get image: {response.status}")
                return await response.read()

    async def wait_for_completion(
        self,
        prompt_id: str,
        timeout: int = 300,
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Wait for a prompt to complete using polling.

        Args:
            prompt_id: The prompt ID to wait for
            timeout: Maximum wait time in seconds
            on_progress: Optional callback for progress updates (current, total)

        Returns:
            History data for the completed prompt
        """
        import asyncio

        start_time = asyncio.get_event_loop().time()

        while True:
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Timeout waiting for prompt {prompt_id}")

            # Check queue status
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/queue") as response:
                    queue_data = await response.json()

            # Check if prompt is still running
            running = queue_data.get("queue_running", [])
            pending = queue_data.get("queue_pending", [])

            prompt_running = any(item[1] == prompt_id for item in running)
            prompt_pending = any(item[1] == prompt_id for item in pending)

            if not prompt_running and not prompt_pending:
                # Prompt finished, get history
                history = await self.get_history(prompt_id)
                if history:
                    return history

            # Wait before next poll
            await asyncio.sleep(0.5)

    async def generate_image(
        self,
        workflow: Dict[str, Any],
        timeout: int = 300,
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> bytes:
        """
        Generate an image using a workflow and return the result.

        Args:
            workflow: ComfyUI workflow JSON
            timeout: Maximum wait time in seconds
            on_progress: Optional progress callback

        Returns:
            Generated image bytes
        """
        # Queue the prompt
        prompt_id = await self.queue_prompt(workflow)

        # Wait for completion
        history = await self.wait_for_completion(prompt_id, timeout, on_progress)

        # Extract image from outputs
        outputs = history.get("outputs", {})
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                image_info = node_output["images"][0]
                return await self.get_image(
                    image_info["filename"],
                    image_info.get("subfolder", ""),
                    image_info.get("type", "output")
                )

        raise Exception("No image found in output")

    async def generate_dual_images(
        self,
        workflow: Dict[str, Any],
        timeout: int = 300,
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> Tuple[bytes, bytes]:
        """
        Generate two images using a dual-branch workflow.

        This method is optimized for battle generation where we need two images
        with different LoRAs but the same base model and parameters.

        Args:
            workflow: Dual-branch ComfyUI workflow JSON (with two SaveImage nodes)
            timeout: Maximum wait time in seconds
            on_progress: Optional progress callback

        Returns:
            Tuple of (left_image_bytes, right_image_bytes)
        """
        # Queue the prompt
        prompt_id = await self.queue_prompt(workflow)

        # Wait for completion
        history = await self.wait_for_completion(prompt_id, timeout, on_progress)

        # Extract both images from outputs
        outputs = history.get("outputs", {})
        left_image = None
        right_image = None

        for node_id, node_output in outputs.items():
            if "images" in node_output:
                image_info = node_output["images"][0]
                filename = image_info["filename"]
                image_bytes = await self.get_image(
                    filename,
                    image_info.get("subfolder", ""),
                    image_info.get("type", "output")
                )

                # Determine which image this is based on filename prefix
                # Node 9 saves with left prefix, Node 19 saves with right prefix
                if node_id == "9":
                    left_image = image_bytes
                elif node_id == "19":
                    right_image = image_bytes
                elif "left" in filename.lower():
                    left_image = image_bytes
                elif "right" in filename.lower():
                    right_image = image_bytes

        if left_image is None or right_image is None:
            raise Exception(
                f"Failed to extract both images from dual workflow. "
                f"Left: {'found' if left_image else 'missing'}, "
                f"Right: {'found' if right_image else 'missing'}"
            )

        return left_image, right_image
