"""Belle configuration package.

Содержит код конфигурации (config.py) и конфиг-данные (belle.conf, conf.d/).
В контейнере папка монтируется в /etc/belle.
"""

from .config import BelleConfig

__all__ = ["BelleConfig"]
