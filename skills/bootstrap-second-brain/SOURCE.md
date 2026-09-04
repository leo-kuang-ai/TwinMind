# Source 与分发边界

- starter_source_commit: `820849e0fa1d611586933948c580091d10868a2e`
- starter_digest: `54e26fb4f35a27185c4f995d01208d59446dd9919d76651cf1196d0ad58e24d0`
- distribution_boundary: `public-github-mit`
- license_status: `MIT`
- canonical_source: `skills/bootstrap-second-brain/`
- starter_source: `我的第二大脑/`
- exclusion_policy: canonical 根 `AGENTS.md` 为宿主适配层不入分发投影；两份历史交付记录（宿主细节）按 `99_维护记录/*交付记录*` 口径排除，理由见 docs/TwinMind第二大脑初始化Skill技术方案.md

此 Skill 采用同目录 `LICENSE` 中的 MIT License。正式 GitHub 源码发布必须在工作树干净后冻结 `release_commit`，并核验 canonical 远端分支 SHA 及该提交中的 LICENSE/SOURCE 文件。独立 ZIP 的 SHA-256 只证明字节一致；未通过 bundle/attestation 双签名、独立渠道 Owner 公钥指纹、预先可信 OpenSSH verifier 和包内容校验的 ZIP，不得跨机器分发或安装。
