local root = vim.env.ZRC_TEST_ROOT
local init = root .. "/profiles/ink/files/.config/nvim"
for _, file in ipairs(vim.fn.glob(init .. "/**/*.lua", false, true)) do
  assert(loadfile(file), "Lua syntax: " .. file)
end
assert(vim.g.colors_name == "zrc-ink")
assert(vim.api.nvim_get_hl(0, { name = "Normal" }).bg == tonumber("161412", 16))
assert(not package.loaded["zrc.lsp"], "LSP must remain lazy before opening a supported file")
local context = require("zrc.context").collect()
assert(context.schema == "zrc.context.v1" and context.contents == nil)
local selected
require("zrc.picker").open({ { label = "alpha", value = 1 }, { label = "beta", value = 2 } },
  "Test picker", function(item) selected = item.value end)
local input = vim.api.nvim_get_current_buf()
vim.api.nvim_buf_set_lines(input, 0, -1, false, { "  › beta" })
vim.api.nvim_exec_autocmds("TextChangedI", { buffer = input })
assert(vim.wait(150, function()
  for _, win in ipairs(vim.api.nvim_list_wins()) do
    local b = vim.api.nvim_win_get_buf(win)
    if b ~= input and vim.bo[b].buftype == "nofile" then
      local content = table.concat(vim.api.nvim_buf_get_lines(b, 0, -1, false), "\n")
      if content:find("beta") and not content:find("alpha") then return true end
    end
  end
end, 10), "picker did not filter")
for _, mapping in ipairs(vim.api.nvim_buf_get_keymap(input, "i")) do
  if mapping.lhs == "<CR>" then mapping.callback(); break end
end
assert(vim.wait(100, function() return selected == 2 end, 10), "picker did not select original value")
assert(#vim.api.nvim_list_wins() == 1, "picker leaked a window")
require("zrc.welcome").open()
local welcome = vim.api.nvim_get_current_buf()
assert(table.concat(vim.api.nvim_buf_get_lines(welcome, 0, -1, false), "\n"):find("oh my ztty"))
require("zrc.picker").open({ { label = "cancel" } }, "Test", function() end)
assert(not vim.wo[vim.api.nvim_list_wins()[1]].number, "dashboard options changed on picker entry")
input = vim.api.nvim_get_current_buf()
for _, mapping in ipairs(vim.api.nvim_buf_get_keymap(input, "i")) do
  if mapping.lhs == "<Esc>" then mapping.callback(); break end
end
vim.cmd.enew()
local file = vim.env.ZRC_TEST_LARGE_FILE
vim.cmd.edit(vim.fn.fnameescape(file))
assert(vim.b.zrc_large_file == true, "large file mode missing")
assert(vim.bo.syntax == "" and not vim.bo.undofile, "large file work was not bounded")
-- LSP launches only a matching installed executable at a recognized project root.
local old_exec, old_start, old_root = vim.fn.executable, vim.lsp.start, vim.fs.root
local captured
vim.fn.executable = function(name) return name:find("/mason/bin/rust%-analyzer$") and 1 or 0 end
vim.lsp.start = function(config) captured = config; return 1 end
vim.fs.root = function() return "/test/project" end
vim.b.zrc_large_file = false
vim.bo.filetype = "rust"
require("zrc.lsp").attach(0)
assert(captured and captured.cmd[1]:find("/mason/bin/rust%-analyzer$"), "Mason fallback not reused")
captured = nil
vim.b.zrc_large_file = true
require("zrc.lsp").attach(0)
assert(captured == nil, "large file started LSP")
vim.fn.executable, vim.lsp.start, vim.fs.root = old_exec, old_start, old_root
-- Exercise the explicit ssmcp split without launching a real service.
local old_job = vim.fn.jobstart
local connected
vim.fn.executable = function(name) return name == "ssmcp" and 1 or old_exec(name) end
vim.fn.jobstart = function(argv, opts) connected = argv[1] == "ssmcp" and opts.term; return 1 end
require("zrc.context").connect()
assert(connected, "explicit ssmcp connection did not create a terminal command")
vim.cmd.stopinsert()
vim.cmd.close()
vim.fn.executable, vim.fn.jobstart = old_exec, old_job
-- Exercise real asynchronous ripgrep with spaces and ignored paths.
local old_cwd = vim.uv.cwd()
vim.cmd.cd(vim.env.ZRC_TEST_FIXTURE)
local picker = require("zrc.picker")
local old_open, found = picker.open, nil
picker.open = function(items) found = items end
require("zrc.search").files()
assert(vim.wait(3000, function() return found ~= nil end, 10), "asynchronous file search timed out")
local has_space = false
for _, item in ipairs(found) do
  assert(not item.label:find(".git/", 1, true), "file search traversed .git")
  if item.label == "space name.txt" then has_space = true end
end
assert(has_space, "file search lost spaced filenames")
picker.open = old_open
local old_input = vim.ui.input
vim.ui.input = function(_, callback) callback("zrc_needle") end
require("zrc.search").grep()
assert(vim.wait(3000, function() return #vim.fn.getqflist() > 0 end, 10), "text search timed out")
local match = vim.fn.getqflist()[1]
assert(match.lnum == 2 and match.col == 1, "text search lost source coordinates")
vim.ui.input = old_input
-- Starting from HOME asks for a project and never launches a whole-home scan.
local old_system, asked = vim.system, false
vim.cmd.cd(vim.uv.os_homedir())
vim.system = function() error("whole-home scan was launched") end
vim.ui.input = function(opts, callback)
  assert(opts.prompt == "Project directory: ")
  asked = true
  callback(nil)
end
require("zrc.search").files()
assert(asked, "home search did not request a project")
vim.system, vim.ui.input = old_system, old_input
vim.cmd.cd(old_cwd)
print("PASS: Lua, palette, context, lazy LSP, picker, welcome, large file, Mason, explicit connect, real rg")
vim.cmd("qa!")
