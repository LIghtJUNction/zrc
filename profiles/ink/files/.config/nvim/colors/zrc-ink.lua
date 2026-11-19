vim.cmd("highlight clear")
vim.g.colors_name = "zrc-ink"
vim.o.background = "dark"
local c = { bg = "#161412", surface = "#201d1a", raised = "#2a2521", fg = "#e8ded2",
  muted = "#a3978b", faint = "#6f655c", copper = "#d4a373", error = "#e59a91",
  lilac = "#c5a4b6", select = "#45382e" }
local groups = {
  Normal = { fg = c.fg, bg = c.bg }, NormalFloat = { fg = c.fg, bg = c.surface },
  FloatBorder = { fg = c.surface, bg = c.surface }, FloatTitle = { fg = c.copper, bg = c.surface, bold = true },
  Comment = { fg = c.muted, italic = true }, Constant = { fg = c.copper },
  String = { fg = "#d7c7a4" }, Number = { fg = c.copper }, Boolean = { fg = c.lilac },
  Identifier = { fg = c.fg }, Function = { fg = c.copper },
  Statement = { fg = c.lilac }, PreProc = { fg = c.lilac }, Type = { fg = c.copper },
  Special = { fg = "#d6bba5" }, Delimiter = { fg = c.muted },
  Error = { fg = c.error, bg = c.bg }, Todo = { fg = c.copper, bold = true },
  LineNr = { fg = c.faint }, CursorLineNr = { fg = c.copper, bold = true },
  CursorLine = { bg = c.surface }, SignColumn = { bg = c.bg }, EndOfBuffer = { fg = c.bg },
  Visual = { bg = c.select }, Search = { fg = c.fg, bg = c.select },
  IncSearch = { fg = c.bg, bg = c.copper }, CurSearch = { fg = c.bg, bg = c.copper },
  MatchParen = { fg = c.copper, underline = true }, NonText = { fg = c.faint },
  Whitespace = { fg = c.faint }, SpecialKey = { fg = c.faint },
  Pmenu = { fg = c.muted, bg = c.surface }, PmenuSel = { fg = c.fg, bg = c.select, bold = true },
  PmenuSbar = { bg = c.raised }, PmenuThumb = { bg = c.faint },
  StatusLine = { fg = c.muted, bg = c.surface }, StatusLineNC = { fg = c.faint, bg = c.surface },
  WinSeparator = { fg = c.surface, bg = c.bg }, VertSplit = { fg = c.surface, bg = c.bg },
  TabLine = { fg = c.muted, bg = c.bg }, TabLineSel = { fg = c.copper, bg = c.bg, bold = true },
  TabLineFill = { bg = c.bg }, Directory = { fg = c.copper }, Title = { fg = c.fg, bold = true },
  Question = { fg = c.copper }, MoreMsg = { fg = c.muted }, ModeMsg = { fg = c.copper },
  ErrorMsg = { fg = c.error }, WarningMsg = { fg = c.copper },
  DiffAdd = { bg = "#302b21" }, DiffChange = { bg = "#302729" },
  DiffDelete = { fg = c.error, bg = "#322322" }, DiffText = { bg = c.select },
  Folded = { fg = c.muted, bg = c.surface }, FoldColumn = { fg = c.faint },
  DiagnosticError = { fg = c.error }, DiagnosticWarn = { fg = c.copper },
  DiagnosticInfo = { fg = c.muted }, DiagnosticHint = { fg = c.lilac },
  DiagnosticUnderlineError = { sp = c.error, undercurl = true },
  DiagnosticUnderlineWarn = { sp = c.copper, undercurl = true },
  DiagnosticUnderlineInfo = { sp = c.muted, undercurl = true },
  DiagnosticUnderlineHint = { sp = c.lilac, undercurl = true },
  ZrcMode = { fg = c.copper, bg = c.surface, bold = true },
  ZrcTitle = { fg = c.fg, bold = true },
  ZrcAccent = { fg = c.copper }, ZrcQuiet = { fg = c.faint },
  ZrcPickerActive = { fg = c.fg, bg = c.select, bold = true },
}
for name, definition in pairs(groups) do vim.api.nvim_set_hl(0, name, definition) end
for name, target in pairs({
  ["@variable"] = "Identifier", ["@variable.parameter"] = "Identifier",
  ["@function"] = "Function", ["@function.call"] = "Function", ["@method"] = "Function",
  ["@keyword"] = "Statement", ["@keyword.function"] = "Statement",
  ["@string"] = "String", ["@number"] = "Number", ["@type"] = "Type",
  ["@comment"] = "Comment", ["@punctuation"] = "Delimiter",
}) do vim.api.nvim_set_hl(0, name, { link = target }) end
for i, color in ipairs({ "#302a25", "#dc8e84", "#c4b18b", "#d9b67e", "#bea38f", "#c5a4b6",
  "#c9b3a0", "#d7ccbf", "#817569", "#edaaa0", "#d7c7a4", "#edd0a0", "#d6bba5", "#ddbfce",
  "#e0cbb8", "#f3eadf" }) do vim.g["terminal_color_" .. (i - 1)] = color end
