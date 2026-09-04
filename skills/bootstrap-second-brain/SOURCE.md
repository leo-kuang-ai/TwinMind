# Source 与分发边界

- starter_source_commit: `58836f306fd50c161328af666481b19bb9ad4768`
- starter_digest: `86d318c8a8e42ead9d0b9d921950725852ea19eb52400df30af79a51734ea484`
- distribution_boundary: `public-github-mit`
- license_status: `MIT`
- canonical_source: `skills/bootstrap-second-brain/`
- starter_source: `我的第二大脑/`

此 Skill 采用同目录 `LICENSE` 中的 MIT License。正式 GitHub 源码发布必须在工作树干净后冻结 `release_commit`，并核验 canonical 远端分支 SHA 及该提交中的 LICENSE/SOURCE 文件。独立 ZIP 的 SHA-256 只证明字节一致；未通过 bundle/attestation 双签名、独立渠道 Owner 公钥指纹、预先可信 OpenSSH verifier 和包内容校验的 ZIP，不得跨机器分发或安装。
