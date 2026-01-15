"""
Browser Fingerprint Randomization

Generates and manages randomized browser fingerprints to evade detection.
Randomizes Canvas, WebGL, fonts, screen resolution, and other browser properties.
"""

import hashlib
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class FingerprintConfig:
    """Configuration for fingerprint generation"""
    # Canvas fingerprinting
    randomize_canvas: bool = True
    canvas_noise_level: float = 0.001  # Small noise to avoid detection

    # WebGL fingerprinting
    randomize_webgl: bool = True
    webgl_vendor_options: List[str] = field(default_factory=lambda: [
        "Intel Inc.",
        "NVIDIA Corporation",
        "AMD",
        "Google Inc. (Intel)",
        "Google Inc. (NVIDIA)",
    ])
    webgl_renderer_options: List[str] = field(default_factory=lambda: [
        "Intel Iris OpenGL Engine",
        "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0)",
        "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Ti Direct3D11 vs_5_0 ps_5_0)",
        "AMD Radeon Pro 5500M OpenGL Engine",
    ])

    # Screen and window
    randomize_screen: bool = True
    screen_resolutions: List[tuple] = field(default_factory=lambda: [
        (1920, 1080),
        (1366, 768),
        (1440, 900),
        (1536, 864),
        (1600, 900),
        (2560, 1440),
    ])

    # Fonts
    randomize_fonts: bool = True

    # Hardware
    randomize_hardware: bool = True
    cpu_cores_options: List[int] = field(default_factory=lambda: [2, 4, 6, 8, 12, 16])
    device_memory_options: List[int] = field(default_factory=lambda: [2, 4, 8, 16, 32])

    # Timezone
    randomize_timezone: bool = True
    timezone_options: List[str] = field(default_factory=lambda: [
        "America/New_York",
        "America/Los_Angeles",
        "America/Chicago",
        "Europe/London",
        "Europe/Paris",
        "Asia/Shanghai",
        "Asia/Tokyo",
    ])

    # Language
    language_options: List[str] = field(default_factory=lambda: [
        "en-US",
        "en-GB",
        "zh-CN",
        "ja-JP",
        "ko-KR",
    ])


class FingerprintGenerator:
    """
    Generates randomized browser fingerprints.

    Features:
    - Canvas fingerprint randomization
    - WebGL fingerprint randomization
    - Font fingerprint randomization
    - Screen resolution randomization
    - Hardware concurrency randomization
    - Timezone and language randomization
    """

    def __init__(self, config: Optional[FingerprintConfig] = None):
        """
        Initialize fingerprint generator.

        Args:
            config: Fingerprint configuration
        """
        self.config = config or FingerprintConfig()
        logger.info("FingerprintGenerator initialized")

    def generate(self) -> Dict[str, Any]:
        """
        Generate a complete random fingerprint.

        Returns:
            Fingerprint dictionary
        """
        fingerprint = {}

        if self.config.randomize_canvas:
            fingerprint["canvas"] = self._generate_canvas_fingerprint()

        if self.config.randomize_webgl:
            fingerprint["webgl"] = self._generate_webgl_fingerprint()

        if self.config.randomize_screen:
            fingerprint["screen"] = self._generate_screen_fingerprint()

        if self.config.randomize_fonts:
            fingerprint["fonts"] = self._generate_font_fingerprint()

        if self.config.randomize_hardware:
            fingerprint["hardware"] = self._generate_hardware_fingerprint()

        if self.config.randomize_timezone:
            fingerprint["timezone"] = random.choice(self.config.timezone_options)

        fingerprint["language"] = random.choice(self.config.language_options)

        # Generate a unique fingerprint ID
        fingerprint["id"] = self._generate_fingerprint_id(fingerprint)

        logger.debug(f"Generated fingerprint: {fingerprint['id']}")
        return fingerprint

    def _generate_canvas_fingerprint(self) -> Dict[str, Any]:
        """
        Generate canvas fingerprint parameters.

        Returns:
            Canvas fingerprint dictionary
        """
        return {
            "noise_level": self.config.canvas_noise_level,
            "noise_seed": random.randint(1, 1000000),
            "text_baseline": random.choice(["top", "hanging", "middle", "alphabetic", "ideographic", "bottom"]),
            "text_align": random.choice(["start", "end", "left", "right", "center"]),
        }

    def _generate_webgl_fingerprint(self) -> Dict[str, Any]:
        """
        Generate WebGL fingerprint parameters.

        Returns:
            WebGL fingerprint dictionary
        """
        return {
            "vendor": random.choice(self.config.webgl_vendor_options),
            "renderer": random.choice(self.config.webgl_renderer_options),
            "version": random.choice([
                "WebGL 1.0 (OpenGL ES 2.0 Chromium)",
                "WebGL 2.0 (OpenGL ES 3.0 Chromium)",
            ]),
            "shading_language_version": random.choice([
                "WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)",
                "WebGL GLSL ES 3.0 (OpenGL ES GLSL ES 3.0 Chromium)",
            ]),
            "max_texture_size": random.choice([4096, 8192, 16384]),
            "max_viewport_dims": random.choice([4096, 8192, 16384]),
        }

    def _generate_screen_fingerprint(self) -> Dict[str, Any]:
        """
        Generate screen fingerprint parameters.

        Returns:
            Screen fingerprint dictionary
        """
        width, height = random.choice(self.config.screen_resolutions)

        # Available dimensions (excluding taskbar)
        avail_height = height - random.choice([40, 48, 60])

        # Color depth
        color_depth = random.choice([24, 30, 32])

        # Pixel depth
        pixel_depth = color_depth

        return {
            "width": width,
            "height": height,
            "avail_width": width,
            "avail_height": avail_height,
            "color_depth": color_depth,
            "pixel_depth": pixel_depth,
            "orientation": random.choice(["landscape-primary", "portrait-primary"]),
        }

    def _generate_font_fingerprint(self) -> Dict[str, Any]:
        """
        Generate font fingerprint parameters.

        Returns:
            Font fingerprint dictionary
        """
        # Common fonts to include
        base_fonts = [
            "Arial", "Verdana", "Helvetica", "Tahoma", "Trebuchet MS",
            "Times New Roman", "Georgia", "Garamond", "Courier New",
            "Brush Script MT", "Comic Sans MS", "Impact", "Palatino",
        ]

        # Additional fonts to randomly include
        additional_fonts = [
            "Calibri", "Cambria", "Consolas", "Constantia", "Corbel",
            "Candara", "Franklin Gothic", "Arial Narrow", "Arial Black",
            "Century Gothic", "Book Antiqua", "Bookman Old Style",
        ]

        # Randomly select subset of additional fonts
        num_additional = random.randint(5, len(additional_fonts))
        selected_additional = random.sample(additional_fonts, num_additional)

        all_fonts = base_fonts + selected_additional
        random.shuffle(all_fonts)

        return {
            "fonts": all_fonts,
            "count": len(all_fonts),
        }

    def _generate_hardware_fingerprint(self) -> Dict[str, Any]:
        """
        Generate hardware fingerprint parameters.

        Returns:
            Hardware fingerprint dictionary
        """
        return {
            "cpu_cores": random.choice(self.config.cpu_cores_options),
            "device_memory": random.choice(self.config.device_memory_options),
            "max_touch_points": random.choice([0, 5, 10]),
            "platform": random.choice([
                "Win32",
                "MacIntel",
                "Linux x86_64",
            ]),
        }

    def _generate_fingerprint_id(self, fingerprint: Dict[str, Any]) -> str:
        """
        Generate a unique ID for the fingerprint.

        Args:
            fingerprint: Fingerprint dictionary

        Returns:
            Fingerprint ID (hash)
        """
        # Create a string representation of the fingerprint
        fp_str = str(sorted(fingerprint.items()))
        # Generate hash
        fp_hash = hashlib.md5(fp_str.encode()).hexdigest()[:16]
        return fp_hash

    async def apply_to_playwright(self, page: Any, fingerprint: Dict[str, Any]) -> None:
        """
        Apply fingerprint to a Playwright page.

        Args:
            page: Playwright page object
            fingerprint: Fingerprint to apply
        """
        try:
            # Inject fingerprint script
            await page.add_init_script(self._generate_playwright_script(fingerprint))
            logger.debug("Applied fingerprint to Playwright page")
        except Exception as e:
            logger.error(f"Failed to apply fingerprint to Playwright: {str(e)}")

    def _generate_playwright_script(self, fingerprint: Dict[str, Any]) -> str:
        """
        Generate JavaScript to inject fingerprint.

        Args:
            fingerprint: Fingerprint dictionary

        Returns:
            JavaScript code
        """
        script_parts = []

        # Canvas fingerprinting
        if "canvas" in fingerprint:
            canvas = fingerprint["canvas"]
            script_parts.append(f"""
                // Canvas fingerprint
                const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;

                HTMLCanvasElement.prototype.toDataURL = function() {{
                    const noise = {canvas['noise_level']};
                    const seed = {canvas['noise_seed']};
                    // Add slight noise to canvas data
                    const context = this.getContext('2d');
                    const imageData = context.getImageData(0, 0, this.width, this.height);
                    for (let i = 0; i < imageData.data.length; i += 4) {{
                        const random = Math.sin(seed + i) * 10000;
                        const delta = (random - Math.floor(random)) * noise;
                        imageData.data[i] += delta;
                    }}
                    context.putImageData(imageData, 0, 0);
                    return originalToDataURL.apply(this, arguments);
                }};
            """)

        # WebGL fingerprinting
        if "webgl" in fingerprint:
            webgl = fingerprint["webgl"]
            script_parts.append(f"""
                // WebGL fingerprint
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {{
                    if (parameter === 37445) {{
                        return '{webgl['vendor']}';
                    }}
                    if (parameter === 37446) {{
                        return '{webgl['renderer']}';
                    }}
                    return getParameter.apply(this, arguments);
                }};
            """)

        # Screen fingerprint
        if "screen" in fingerprint:
            screen = fingerprint["screen"]
            script_parts.append(f"""
                // Screen fingerprint
                Object.defineProperty(screen, 'width', {{get: () => {screen['width']}}});
                Object.defineProperty(screen, 'height', {{get: () => {screen['height']}}});
                Object.defineProperty(screen, 'availWidth', {{get: () => {screen['avail_width']}}});
                Object.defineProperty(screen, 'availHeight', {{get: () => {screen['avail_height']}}});
                Object.defineProperty(screen, 'colorDepth', {{get: () => {screen['color_depth']}}});
                Object.defineProperty(screen, 'pixelDepth', {{get: () => {screen['pixel_depth']}}});
            """)

        # Hardware fingerprint
        if "hardware" in fingerprint:
            hardware = fingerprint["hardware"]
            script_parts.append(f"""
                // Hardware fingerprint
                Object.defineProperty(navigator, 'hardwareConcurrency', {{get: () => {hardware['cpu_cores']}}});
                Object.defineProperty(navigator, 'deviceMemory', {{get: () => {hardware['device_memory']}}});
                Object.defineProperty(navigator, 'maxTouchPoints', {{get: () => {hardware['max_touch_points']}}});
            """)

        # Language
        if "language" in fingerprint:
            lang = fingerprint["language"]
            script_parts.append(f"""
                // Language
                Object.defineProperty(navigator, 'language', {{get: () => '{lang}'}});
                Object.defineProperty(navigator, 'languages', {{get: () => ['{lang}']}});
            """)

        # Timezone
        if "timezone" in fingerprint:
            timezone = fingerprint["timezone"]
            script_parts.append(f"""
                // Timezone
                Date.prototype.getTimezoneOffset = function() {{
                    // This is a simplified version; real implementation would be more complex
                    return -new Intl.DateTimeFormat('en-US', {{
                        timeZone: '{timezone}'
                    }}).resolvedOptions().timeZone.offset || 0;
                }};
            """)

        # Additional anti-detection measures
        script_parts.append("""
            // Remove webdriver flag
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

            // Plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format'},
                    {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: ''},
                    {name: 'Native Client', filename: 'internal-nacl-plugin', description: ''},
                ]
            });

            // Permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({state: Notification.permission}) :
                    originalQuery(parameters)
            );

            // Chrome runtime
            window.chrome = {
                runtime: {}
            };
        """)

        return "\n".join(script_parts)

    def generate_consistent_fingerprint(self, seed: str) -> Dict[str, Any]:
        """
        Generate a consistent fingerprint based on a seed.
        Useful for maintaining the same fingerprint across sessions.

        Args:
            seed: Seed string for random generation

        Returns:
            Fingerprint dictionary
        """
        # Set random seed
        random.seed(hash(seed))

        # Generate fingerprint
        fingerprint = self.generate()

        # Reset random seed
        random.seed()

        logger.debug(f"Generated consistent fingerprint from seed: {seed}")
        return fingerprint


# Utility functions
def get_common_screen_resolutions() -> List[tuple]:
    """
    Get list of common screen resolutions.

    Returns:
        List of (width, height) tuples
    """
    return [
        (1920, 1080),  # Full HD
        (1366, 768),   # HD
        (1440, 900),   # WXGA+
        (1536, 864),   # HD+
        (1600, 900),   # HD+
        (2560, 1440),  # QHD
        (3840, 2160),  # 4K
    ]


def get_common_user_agents() -> List[str]:
    """
    Get list of common user agents.

    Returns:
        List of user agent strings
    """
    return [
        # Chrome Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Chrome Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Firefox Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        # Safari Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        # Edge Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ]
