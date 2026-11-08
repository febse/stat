-- Turns `::: {.video title="..."}` into a collapsed callout with a play icon.
function Div(el)
  if not el.classes:includes("video") then return nil end
  el.classes:insert("callout-note")
  if el.attributes["collapse"] == nil then el.attributes["collapse"] = "true" end
  if el.attributes["appearance"] == nil then el.attributes["appearance"] = "simple" end
  if el.attributes["title"] == nil then el.attributes["title"] = "Video (click to expand)" end
  return el
end
