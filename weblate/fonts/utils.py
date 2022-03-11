#
# Copyright © 2012–2022 Michal Čihař <michal@cihar.com>
#
# This file is part of Weblate <https://weblate.org/>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""Font handling wrapper."""


import os
from functools import lru_cache
from io import BytesIO
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.core.cache import cache
from django.utils.html import escape
from PIL import ImageFont

from weblate.utils.checks import weblate_check
from weblate.utils.data import data_dir

FONTCONFIG_CONFIG = """<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
    <cachedir>{}</cachedir>
    <dir>{}</dir>
    <dir>{}</dir>
    <dir>{}</dir>
    <dir>{}</dir>
    <dir>{}</dir>
    <config>
        <rescan>
            <int>30</int>
        </rescan>
    </config>

    <alias>
        <family>sans-serif</family>
        <prefer>
            <family>Source Sans 3</family>
            <family>DejaVu Sans</family>
            <family>Noto Sans</family>
            <family>Droid Sans Fallback</family>
        </prefer>
    </alias>

    <alias>
        <family>Source Sans 3</family>
        <default><family>sans-serif</family></default>
    </alias>

    <alias>
        <family>DejaVu Sans</family>
        <default><family>sans-serif</family></default>
    </alias>

    <!--
     Synthetic emboldening for fonts that do not have bold face available
    -->
    <match target="font">
        <test name="weight" compare="less_eq">
            <const>medium</const>
        </test>
        <test target="pattern" name="weight" compare="more_eq">
            <const>bold</const>
        </test>
        <edit name="embolden" mode="assign">
            <bool>true</bool>
        </edit>
        <edit name="weight" mode="assign">
            <const>bold</const>
        </edit>
    </match>
</fontconfig>
"""

FONT_WEIGHTS = {
    "normal": None,
    "light": None,
    "bold": None,
    "": None,
}


def configure_fontconfig():
    """Configures fontconfig to use custom configuration."""
    if getattr(configure_fontconfig, "is_configured", False):
        return

    fonts_dir = data_dir("fonts")
    config_name = os.path.join(fonts_dir, "fonts.conf")

    if not os.path.exists(fonts_dir):
        os.makedirs(fonts_dir)

    # Generate the configuration
    with open(config_name, "w") as handle:
        handle.write(
            FONTCONFIG_CONFIG.format(
                data_dir("cache", "fonts"),
                fonts_dir,
                os.path.join(settings.STATIC_ROOT, "vendor", "font-source", "TTF"),
                os.path.join(settings.STATIC_ROOT, "vendor", "font-dejavu"),
                os.path.join(settings.STATIC_ROOT, "font-noto"),
                os.path.join(settings.STATIC_ROOT, "font-droid"),
            )
        )

    # Inject into environment
    os.environ["FONTCONFIG_FILE"] = config_name

    configure_fontconfig.is_configured = True


def get_font_weight(weight):
    return FONT_WEIGHTS[weight]


@lru_cache(maxsize=512)
def render_size(font, weight, size, spacing, text, width=1000, lines=1, cache_key=None):
    """Check whether rendered text fits."""
    raise NotImplementedError()


def check_render_size(font, weight, size, spacing, text, width, lines, cache_key=None):
    """Checks whether rendered text fits."""
    size, actual_lines = render_size(
        font, weight, size, spacing, text, width, lines, cache_key
    )
    return size.width <= width and actual_lines <= lines


def get_font_name(filelike):
    """Returns tuple of font family and style, for example ('Ubuntu', 'Regular')."""
    if not hasattr(filelike, "loaded_font"):
        # The tempfile creation is workaroud for Pillow crashing on invalid font
        # see https://github.com/python-pillow/Pillow/issues/3853
        # Once this is fixed, it should be possible to directly operate on filelike
        temp = NamedTemporaryFile(delete=False)
        try:
            temp.write(filelike.read())
            filelike.seek(0)
            temp.close()
            filelike.loaded_font = ImageFont.truetype(temp.name)
        finally:
            os.unlink(temp.name)
    return filelike.loaded_font.getname()


def check_fonts(app_configs=None, **kwargs):
    """Checks font rendering."""
    return [weblate_check("weblate.C024", f"Failed to use Pango")]
