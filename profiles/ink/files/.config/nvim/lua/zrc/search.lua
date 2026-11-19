local M = {}
local function open_file(item)
  vim.cmd.edit(vim.fn.fnameescape(item.value))
end
local function project_root(callback)
  local home = vim.uv.fs_realpath(vim.uv.os_homedir())
  local markers = { ".git", "Cargo.toml", "package.json", "pyproject.toml", "go.mod" }
  local path = vim.fs.root(0, markers) or vim.uv.cwd()
  local function allowed(candidate)
    local real = vim.uv.fs_realpath(candidate)
    local stat = real and vim.uv.fs_stat(real)
    return real and real ~= "/" and real ~= home and stat and stat.type == "directory", real
  end
  local ok, directory = allowed(path)
  if ok then callback(directory); return end
  vim.ui.input({ prompt = "Project directory: ", completion = "dir" }, function(value)
    if not value or value == "" then return end
    local valid, chosen = allowed(vim.fn.expand(value))
    if valid then callback(chosen)
    else vim.notify("Choose a project directory inside your home, not the whole home.", vim.log.levels.WARN) end
  end)
end
function M.files()
  if vim.fn.executable("rg") ~= 1 then
    vim.ui.input({ prompt = "File: ", completion = "file" }, function(path)
      if path and path ~= "" then open_file({ value = path }) end
    end)
    return
  end
  project_root(function(cwd)
  local limit = require("zrc").options.max_files
  local chunks, bytes, truncated = {}, 0, false
  local process
  process = vim.system({ "rg", "--files", "--hidden", "--null", "-g", "!.git",
    "-g", "!node_modules", "-g", "!target", "-g", "!vendor", "-g", "!.cache" }, {
    cwd = cwd, timeout = 5000,
    stdout = function(err, data)
      if err or not data then return end
      bytes = bytes + #data
      if bytes <= 512 * 1024 then chunks[#chunks + 1] = data
      else truncated = true; if process then process:kill(15) end end
    end,
  }, function(result)
    if result.code == 124 then truncated = true end
    vim.schedule(function()
      if result.code ~= 0 and result.code ~= 1 and not truncated then
        vim.notify("File search failed: " .. (result.stderr or ""), vim.log.levels.WARN); return
      end
      local items = {}
      for path in table.concat(chunks):gmatch("([^%z]+)%z") do
        if #items >= limit then truncated = true; break end
        items[#items + 1] = { label = path, value = cwd .. "/" .. path }
      end
      require("zrc.picker").open(items, truncated and "Files · bounded result" or "Files", open_file)
    end)
  end)
  end)
end
function M.recent()
  local items = {}
  for _, path in ipairs(vim.v.oldfiles) do
    if #items >= 100 then break end
    if vim.fn.filereadable(path) == 1 then
      items[#items + 1] = { label = vim.fn.fnamemodify(path, ":~:."), value = path }
    end
  end
  require("zrc.picker").open(items, "Recent", open_file)
end
function M.buffers()
  local items = {}
  for _, buf in ipairs(vim.api.nvim_list_bufs()) do
    if vim.bo[buf].buflisted and vim.bo[buf].buftype == "" then
      local name = vim.api.nvim_buf_get_name(buf)
      items[#items + 1] = { label = name == "" and ("Untitled · " .. buf) or vim.fn.fnamemodify(name, ":~:."), value = buf }
    end
  end
  require("zrc.picker").open(items, "Buffers", function(item) vim.api.nvim_set_current_buf(item.value) end)
end
function M.grep()
  if vim.fn.executable("rg") ~= 1 then vim.notify("Install ripgrep to search text", vim.log.levels.WARN); return end
  project_root(function(cwd)
  vim.ui.input({ prompt = "Search text: " }, function(query)
    if not query or query == "" then return end
    local chunks, bytes, truncated, process = {}, 0, false, nil
    process = vim.system({ "rg", "--json", "--smart-case", "--max-count=20",
      "-g", "!.git", "-g", "!node_modules", "-g", "!target", "--", query, "." }, {
      cwd = cwd, timeout = 5000,
      stdout = function(err, data)
        if err or not data then return end
        bytes = bytes + #data
        if bytes <= 2 * 1024 * 1024 then chunks[#chunks + 1] = data
        else truncated = true; if process then process:kill(15) end end
      end,
    }, function(result)
      if result.code == 124 then truncated = true end
      vim.schedule(function()
        if result.code ~= 0 and result.code ~= 1 and not truncated then
          vim.notify("Search failed: " .. (result.stderr or ""), vim.log.levels.WARN); return
        end
        local items = {}
        for line in table.concat(chunks):gmatch("[^\n]+") do
          if #items >= 1000 then truncated = true; break end
          local ok, event = pcall(vim.json.decode, line)
          if ok and event.type == "match" and event.data.path.text and event.data.lines.text then
            local hit = event.data
            items[#items + 1] = { filename = cwd .. "/" .. hit.path.text, lnum = hit.line_number,
              col = hit.submatches[1] and (hit.submatches[1].start + 1) or 1,
              text = hit.lines.text:gsub("[\r\n]+$", "") }
          end
        end
        vim.fn.setqflist({}, "r", { title = "Search: " .. query .. (truncated and " · truncated" or ""), items = items })
        if #items > 0 then vim.cmd.copen(10) else vim.notify("No matches") end
      end)
    end)
  end)
  end)
end
return M
