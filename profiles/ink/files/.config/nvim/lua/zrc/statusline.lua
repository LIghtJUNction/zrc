local M = {}
local modes = { n = "NORMAL", i = "INSERT", v = "VISUAL", V = "LINES", ["\22"] = "BLOCK",
  c = "COMMAND", R = "REPLACE", t = "TERMINAL", s = "SELECT" }
function M.render()
  if vim.bo.buftype == "nofile" then return "  %#ZrcMode# zrc %*%=%#Comment#oh my ztty  " end
  local mode = vim.api.nvim_get_mode().mode
  local label = modes[mode] or modes[mode:sub(1, 1)] or "NORMAL"
  local details = vim.b.zrc_diagnostic_summary or ""
  local large = vim.b.zrc_large_file and "large file · " or ""
  return "  %#ZrcMode#" .. label .. "%*   %<%f %m%r%=%#Comment#" .. large .. details
    .. "%*  %y   %l:%c  %p%%  "
end
function M.setup()
  vim.o.statusline = "%!v:lua.require'zrc.statusline'.render()"
  vim.api.nvim_create_autocmd("DiagnosticChanged", {
    group = "Zrc", callback = function(args)
      local counts = vim.diagnostic.count(args.buf)
      local parts = {}
      if (counts[1] or 0) > 0 then parts[#parts + 1] = "E " .. counts[1] end
      if (counts[2] or 0) > 0 then parts[#parts + 1] = "W " .. counts[2] end
      vim.b[args.buf].zrc_diagnostic_summary = table.concat(parts, "  ")
    end,
  })
end
return M
