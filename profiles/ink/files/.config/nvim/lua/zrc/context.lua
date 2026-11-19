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
  vim.cmd("botright split")
  vim.cmd("resize 14")
  vim.fn.jobstart({ "ssmcp" }, { term = true })
  vim.cmd.startinsert()
end
return M
