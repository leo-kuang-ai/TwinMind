#!/usr/bin/env python3
"""确定性打包 bootstrap-second-brain，并执行本地结构/发布门禁。"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parents[1]
DIST_ROOT = REPO_ROOT / "dist"
BUNDLE_NAME = "bootstrap-second-brain-v0.1.zip"
ROOT_NAME = "bootstrap-second-brain"
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
ALLOWED_ROOT_FILES = {"LICENSE", "SKILL.md", "SOURCE.md"}
ALLOWED_PREFIXES = ("agents/", "scripts/", "references/", "assets/", "manifests/", "schemas/")
FORBIDDEN_PARTS = {"tests", "evals", "results", "__pycache__", ".git", ".twinmind"}
TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".txt"}


class PackageError(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _contract_module():
    path = SKILL_ROOT / "scripts/contract_validation.py"
    spec = importlib.util.spec_from_file_location("package_contract_validation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def allowed_files() -> list[Path]:
    files = []
    for path in SKILL_ROOT.rglob("*"):
        if path.is_symlink():
            raise PackageError(f"allowlist 不允许 symlink：{path.relative_to(SKILL_ROOT)}")
        if not path.is_file():
            continue
        relative = path.relative_to(SKILL_ROOT)
        posix = relative.as_posix()
        if any(part in FORBIDDEN_PARTS for part in relative.parts):
            continue
        if posix in ALLOWED_ROOT_FILES or posix.startswith(ALLOWED_PREFIXES):
            files.append(path)
    required = {"LICENSE", "schemas/tool-choice.schema.json", "schemas/tool-evidence.schema.json"}
    present = {path.relative_to(SKILL_ROOT).as_posix() for path in files}
    if not required <= present:
        raise PackageError(f"allowlist 缺少必需文件：{sorted(required - present)}")
    return sorted(files, key=lambda path: path.relative_to(SKILL_ROOT).as_posix())


def _scan_file(path: Path, data: bytes) -> None:
    relative = path.relative_to(SKILL_ROOT).as_posix()
    if PurePosixPath(relative).is_absolute() or ".." in PurePosixPath(relative).parts:
        raise PackageError(f"不安全路径：{relative}")
    lowered = path.name.lower()
    if lowered.startswith(".env") or lowered.endswith((".pem", ".key", ".p12", ".pfx")):
        raise PackageError(f"疑似密钥文件：{relative}")
    if path.suffix.lower() in TEXT_SUFFIXES:
        text = data.decode("utf-8")
        forbidden = ("/" + "Users/", "BEGIN " + "PRIVATE KEY", "OPENSSH " + "PRIVATE KEY", "sk" + "-")
        if any(token in text for token in forbidden):
            raise PackageError(f"文本含绝对用户路径或密钥模式：{relative}")


def validate_release_policy(source: dict[str, str], license_text: str) -> None:
    if source["distribution_boundary"] != "public-github-mit":
        raise PackageError("SOURCE.md 发布边界必须为 public-github-mit")
    if source["license_status"] != "MIT":
        raise PackageError("SOURCE.md 许可状态必须为 MIT")
    if not license_text.startswith("MIT License\n\n") or "Permission is hereby granted" not in license_text:
        raise PackageError("Skill LICENSE 不是完整 MIT License")


def _safe_regular_file(path: Path, *, maximum: int, label: str) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise PackageError(f"{label}无法安全打开：{path.name}") from error
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise PackageError(f"{label}不是单链接普通文件：{path.name}")
        if opened.st_size > maximum:
            raise PackageError(f"{label}超过上限：{path.name}")
        data = bytearray()
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, maximum - len(data) + 1))
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > maximum:
                raise PackageError(f"{label}读取期间超过上限：{path.name}")
        final = os.fstat(descriptor)
        if ((final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns)
                != (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)):
            raise PackageError(f"{label}读取期间发生漂移：{path.name}")
        return bytes(data)
    finally:
        os.close(descriptor)


def _validated_source_snapshot() -> list[tuple[Path, bytes]]:
    files = allowed_files()
    snapshot = [(path, _safe_regular_file(path, maximum=16 * 1024 * 1024, label="source 输入"))
                for path in files]
    by_relative = {path.relative_to(SKILL_ROOT).as_posix(): data for path, data in snapshot}
    contracts = _contract_module()
    for relative, data in sorted(by_relative.items()):
        if relative.startswith("schemas/") and relative.endswith(".schema.json"):
            contracts.validate_schema_definition(json.loads(data.decode("utf-8")))
    for path, data in snapshot:
        _scan_file(path, data)
    source = read_source_contract(by_relative["SOURCE.md"].decode("utf-8"))
    starter = json.loads(by_relative["manifests/starter-v1.json"].decode("utf-8"))
    if (source["starter_source_commit"] != starter["source"]["commit"]
            or source["starter_digest"] != starter["source"]["tree_digest"]):
        raise PackageError("SOURCE.md 与 Starter manifest 不一致")
    validate_release_policy(source, by_relative["LICENSE"].decode("utf-8"))
    return snapshot


def validate_source_tree() -> list[Path]:
    return [path for path, _ in _validated_source_snapshot()]


def build_bundle_bytes(snapshot: list[tuple[Path, bytes]] | None = None) -> bytes:
    snapshot = _validated_source_snapshot() if snapshot is None else snapshot
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, data in snapshot:
            relative = path.relative_to(SKILL_ROOT).as_posix()
            info = zipfile.ZipInfo(f"{ROOT_NAME}/{relative}", FIXED_TIME)
            info.create_system = 3
            mode = 0o755 if path.suffix == ".py" else 0o644
            info.external_attr = (0o100000 | mode) << 16
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return output.getvalue()


def verify_bundle_structure(bundle_bytes: bytes,
                            snapshot: list[tuple[Path, bytes]] | None = None) -> None:
    snapshot = _validated_source_snapshot() if snapshot is None else snapshot
    expected = {
        f"{ROOT_NAME}/{path.relative_to(SKILL_ROOT).as_posix()}": data
        for path, data in snapshot
    }
    try:
        with zipfile.ZipFile(io.BytesIO(bundle_bytes)) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise PackageError("bundle 含重复路径")
            if set(names) != set(expected):
                missing = sorted(set(expected) - set(names))
                extra = sorted(set(names) - set(expected))
                raise PackageError(f"bundle allowlist 不一致：missing={missing}, extra={extra}")
            for info in infos:
                path = PurePosixPath(info.filename)
                mode = (info.external_attr >> 16) & 0o177777
                if path.is_absolute() or ".." in path.parts or info.is_dir():
                    raise PackageError(f"bundle 含不安全路径：{info.filename}")
                if stat.S_IFMT(mode) != stat.S_IFREG:
                    raise PackageError(f"bundle 条目不是普通文件：{info.filename}")
                expected_mode = 0o755 if PurePosixPath(info.filename).suffix == ".py" else 0o644
                if stat.S_IMODE(mode) != expected_mode:
                    raise PackageError(f"bundle 权限不一致：{info.filename}")
                if info.file_size != len(expected[info.filename]):
                    raise PackageError(f"bundle 文件大小不一致：{info.filename}")
                if archive.read(info) != expected[info.filename]:
                    raise PackageError(f"bundle 文件内容不一致：{info.filename}")
    except zipfile.BadZipFile as error:
        raise PackageError("bundle 不是有效 ZIP") from error


def read_source_contract(text: str | None = None) -> dict[str, str]:
    if text is None:
        text = _safe_regular_file(SKILL_ROOT / "SOURCE.md", maximum=1024 * 1024,
                                  label="source contract").decode("utf-8")
    result = {}
    for key in ("starter_source_commit", "starter_digest", "distribution_boundary", "license_status"):
        match = re.search(rf"^- {key}: `([^`]+)`$", text, re.MULTILINE)
        if not match:
            raise PackageError(f"SOURCE.md 缺少 {key}")
        result[key] = match.group(1)
    return result


def allowlist_digest(snapshot: list[tuple[Path, bytes]] | None = None) -> str:
    snapshot = _validated_source_snapshot() if snapshot is None else snapshot
    entries = [{"path": path.relative_to(SKILL_ROOT).as_posix(), "sha256": sha256(data)}
               for path, data in snapshot]
    return sha256((json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode())


def write_bundle() -> dict[str, Any]:
    snapshot = _validated_source_snapshot()
    data = build_bundle_bytes(snapshot)
    DIST_ROOT.mkdir(exist_ok=True)
    bundle = DIST_ROOT / BUNDLE_NAME
    bundle.write_bytes(data)
    (DIST_ROOT / f"{BUNDLE_NAME}.sha256").write_text(f"{sha256(data)}  {BUNDLE_NAME}\n", encoding="utf-8")
    return {"status": "ok", "artifact_status": "build-only",
            "distribution_authentication": "unverified",
            "bundle": str(bundle.relative_to(REPO_ROOT)), "sha256": sha256(data),
            "size": len(data)}


def verify_release_trust(*, zip_path: Path, attestation_path: Path, trusted_verifier: Path | None,
                         independent_fingerprint: str | None, execution_sentinel: Path | None = None) -> dict[str, Any]:
    del zip_path, attestation_path, execution_sentinel
    if trusted_verifier is None or independent_fingerprint is None:
        return {"distribution_authentication": "unverified", "command_outcome": "action_required",
                "reason": "缺少 bundle 外可信 OpenSSH verifier 或独立 Owner 指纹"}
    return {"distribution_authentication": "verification-required", "command_outcome": "action_required"}


def create_release_attestation(bundle_bytes: bytes, signer_fingerprint: str) -> dict[str, Any]:
    snapshot = _validated_source_snapshot()
    source_text = next(data for path, data in snapshot
                       if path.relative_to(SKILL_ROOT).as_posix() == "SOURCE.md")
    source = read_source_contract(source_text.decode("utf-8"))
    return {
        "schema_version": 1,
        "package_name": BUNDLE_NAME,
        "package_sha256": sha256(bundle_bytes),
        "package_size": len(bundle_bytes),
        "starter_source_commit": source["starter_source_commit"],
        "starter_digest": source["starter_digest"],
        "allowlist_digest": allowlist_digest(snapshot),
        "builder_version": "bootstrap-second-brain-package-v1",
        "release_boundary": "public-github-mit",
        "zip_namespace": "twinmind-bundle-v1",
        "attestation_namespace": "twinmind-release-attestation-v1",
        "signer_fingerprint": signer_fingerprint,
    }


def _safe_release_file(path: Path) -> bytes:
    return _safe_regular_file(path, maximum=128 * 1024 * 1024, label="release 输入")


def _verify_ssh_signature(verifier: Path, allowed_signers: Path, principal: str,
                          namespace: str, signature: Path, data: bytes) -> None:
    result = subprocess.run(
        [str(verifier), "-Y", "verify", "-f", str(allowed_signers), "-I", principal,
         "-n", namespace, "-s", str(signature)],
        input=data, capture_output=True, check=False,
    )
    if result.returncode != 0:
        raise PackageError(f"OpenSSH signature 验证失败：{namespace}")


def _materialize_private_file(root: Path, name: str, data: bytes, mode: int) -> Path:
    path = root / name
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        offset = 0
        while offset < len(data):
            offset += os.write(descriptor, data[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return path


def verify_signed_release(*, trusted_verifier: Path, verifier_sha256: str, public_key: Path,
                          allowed_signers: Path, principal: str, independent_fingerprint: str,
                          zip_path: Path, zip_signature: Path, attestation_path: Path,
                          attestation_signature: Path) -> dict[str, Any]:
    verifier_bytes = _safe_release_file(trusted_verifier)
    if sha256(verifier_bytes) != verifier_sha256:
        raise PackageError("可信 OpenSSH verifier identity digest 漂移")
    public_key_bytes = _safe_release_file(public_key)
    zip_bytes = _safe_release_file(zip_path)
    attestation_bytes = _safe_release_file(attestation_path)
    zip_signature_bytes = _safe_release_file(zip_signature)
    attestation_signature_bytes = _safe_release_file(attestation_signature)
    allowed_signers_bytes = _safe_release_file(allowed_signers)
    with tempfile.TemporaryDirectory() as temp:
        verification_root = Path(temp)
        public_key_copy = _materialize_private_file(verification_root, "owner.pub",
                                                     public_key_bytes, 0o600)
        allowed_signers_copy = _materialize_private_file(verification_root, "allowed-signers",
                                                         allowed_signers_bytes, 0o600)
        zip_signature_copy = _materialize_private_file(verification_root, "bundle.sig",
                                                       zip_signature_bytes, 0o600)
        attestation_signature_copy = _materialize_private_file(
            verification_root, "attestation.sig", attestation_signature_bytes, 0o600)
        if sha256(_safe_release_file(trusted_verifier)) != verifier_sha256:
            raise PackageError("可信 OpenSSH verifier identity digest 漂移")
        fingerprint_result = subprocess.run(
            [str(trusted_verifier), "-lf", str(public_key_copy), "-E", "sha256"],
            capture_output=True, text=True, check=False,
        )
        fingerprint_fields = fingerprint_result.stdout.split()
        if (fingerprint_result.returncode != 0
                or independent_fingerprint not in fingerprint_fields):
            raise PackageError("独立 Owner 公钥指纹不匹配")
        if sha256(_safe_release_file(trusted_verifier)) != verifier_sha256:
            raise PackageError("可信 OpenSSH verifier identity digest 漂移")
        _verify_ssh_signature(trusted_verifier, allowed_signers_copy, principal,
                              "twinmind-bundle-v1", zip_signature_copy, zip_bytes)
        if sha256(_safe_release_file(trusted_verifier)) != verifier_sha256:
            raise PackageError("可信 OpenSSH verifier identity digest 漂移")
        _verify_ssh_signature(trusted_verifier, allowed_signers_copy, principal,
                              "twinmind-release-attestation-v1", attestation_signature_copy,
                              attestation_bytes)
        if sha256(_safe_release_file(trusted_verifier)) != verifier_sha256:
            raise PackageError("可信 OpenSSH verifier identity digest 漂移")
    try:
        attestation = json.loads(attestation_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise PackageError(f"双签名通过后的 attestation 无法解析：{error}") from error
    _contract_module().validate_contract("release-attestation", attestation)
    expected = create_release_attestation(zip_bytes, independent_fingerprint)
    if attestation != expected:
        raise PackageError("release attestation 与 bundle/source/allowlist 不一致")
    verify_bundle_structure(zip_bytes)
    return {"distribution_authentication": "verified", "command_outcome": "success",
            "package_sha256": sha256(zip_bytes), "signer_fingerprint": independent_fingerprint}


def check_bundle() -> dict[str, Any]:
    first_snapshot = _validated_source_snapshot()
    first = build_bundle_bytes(first_snapshot)
    second_snapshot = _validated_source_snapshot()
    second = build_bundle_bytes(second_snapshot)
    if first != second:
        raise PackageError("同一 source digest 两次打包字节不一致")
    verify_bundle_structure(first, second_snapshot)
    return {"status": "ok", "artifact_status": "build-only",
            "sha256": sha256(first), "size": len(first),
            "allowlist_digest": allowlist_digest(second_snapshot), "distribution_authentication": "unverified"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--write", action="store_true")
    modes.add_argument("--verify-release", action="store_true")
    parser.add_argument("--trusted-verifier")
    parser.add_argument("--verifier-sha256")
    parser.add_argument("--public-key")
    parser.add_argument("--allowed-signers")
    parser.add_argument("--principal")
    parser.add_argument("--independent-fingerprint")
    parser.add_argument("--zip", dest="zip_path")
    parser.add_argument("--zip-signature")
    parser.add_argument("--attestation")
    parser.add_argument("--attestation-signature")
    args = parser.parse_args(argv)
    try:
        if args.check:
            result = check_bundle()
        elif args.write:
            result = write_bundle()
        else:
            supplied = {
                "trusted_verifier": args.trusted_verifier,
                "verifier_sha256": args.verifier_sha256,
                "public_key": args.public_key,
                "allowed_signers": args.allowed_signers,
                "principal": args.principal,
                "independent_fingerprint": args.independent_fingerprint,
                "zip_path": args.zip_path,
                "zip_signature": args.zip_signature,
                "attestation_path": args.attestation,
                "attestation_signature": args.attestation_signature,
            }
            if any(supplied.values()):
                missing = sorted(name for name, value in supplied.items() if not value)
                if missing:
                    raise PackageError(f"正式 release 验证参数不完整：{missing}")
                result = verify_signed_release(
                    trusted_verifier=Path(supplied["trusted_verifier"]),
                    verifier_sha256=supplied["verifier_sha256"],
                    public_key=Path(supplied["public_key"]),
                    allowed_signers=Path(supplied["allowed_signers"]),
                    principal=supplied["principal"],
                    independent_fingerprint=supplied["independent_fingerprint"],
                    zip_path=Path(supplied["zip_path"]),
                    zip_signature=Path(supplied["zip_signature"]),
                    attestation_path=Path(supplied["attestation_path"]),
                    attestation_signature=Path(supplied["attestation_signature"]),
                )
            else:
                result = verify_release_trust(zip_path=DIST_ROOT / BUNDLE_NAME,
                    attestation_path=DIST_ROOT / "release-attestation.json", trusted_verifier=None,
                    independent_fingerprint=None)
    except (OSError, PackageError, ValueError) as error:
        print(json.dumps({"status": "error", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 2 if result.get("command_outcome") == "action_required" else 0


if __name__ == "__main__":
    raise SystemExit(main())
