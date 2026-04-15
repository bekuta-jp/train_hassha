from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LineConfig:
    line_id: str
    line_name: str
    route_page_url: str
    route_selector: str


PORT_LINER_LINE = LineConfig(
    line_id="port_liner",
    line_name="神戸新交通ポートアイランド線",
    route_page_url="https://www.knt-liner.co.jp/ja/station/",
    route_selector="div.v2-routemap-po",
)


DEFAULT_LINE = PORT_LINER_LINE
