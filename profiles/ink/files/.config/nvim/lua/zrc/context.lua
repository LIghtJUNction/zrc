local M = {}
function M.collect()
  local pos = vim.api.nvim_win_get_cursor(0)
  return { schema = "zrc.context.v1", cwd = vim.uv.cwd(), file = vim.api.nvim_buf_get_name(0),
    filetype = vim.bo.filetype, cursor = { line = pos[1], column = pos[2] + 1 },
    modified = vim.bo.modified, diagnostics = vim.diagnostic.count(0) }
end
function M.show()
  local text = vim.json.encode(M.collect())
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, { text })
  vim.bo[buf].filetype, vim.bo[buf].bufhidden, vim.bo[buf].modifiable = "json", "wipe", false
  vim.cmd.vsplit()
  vim.api.nvim_win_set_buf(0, buf)
end
function M.connect()
  if vim.fn.executable("ssmcp") ~= 1 then
    vim.notify("ssmcp is not installed. Run omztty doctor.", vim.log.levels.WARN); return
  end
  local original = vim.api.nvim_get_current_win()
  vim.cmd("botright new")
  local window, buffer = vim.api.nvim_get_current_win(), vim.api.nvim_get_current_buf()
  vim.cmd("resize 14")
  local ok, job = pcall(vim.fn.jobstart, { "ssmcp" }, { term = true })
  if not ok or job <= 0 then
    if vim.api.nvim_win_is_valid(window) then vim.api.nvim_win_close(window, true) end
    if vim.api.nvim_buf_is_valid(buffer) then vim.api.nvim_buf_delete(buffer, { force = true }) end
    if vim.api.nvim_win_is_valid(original) then vim.api.nvim_set_current_win(original) end
    local detail = ok and ("jobstart returned " .. job) or tostring(job)
    vim.notify("Could not start ssmcp: " .. detail, vim.log.levels.ERROR)
    return
  end
  vim.cmd.startinsert()
end
return M
