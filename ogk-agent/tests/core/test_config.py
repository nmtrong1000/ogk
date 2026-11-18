import pytest

from service.core.config import ConfigError, load_config


def test_valid_config(tmp_path, write_config):
    write_config({"server_url": "https://10.0.0.2:8443/", "ca_cert": "ca.crt", "health_interval": 5})
    config = load_config(tmp_path)
    assert config.server_url == "https://10.0.0.2:8443"
    assert config.ca_cert == tmp_path / "ca.crt"
    assert config.health_interval == 5.0
    assert config.ipc_port == 47800


def test_absolute_ca_path_kept(tmp_path, write_config):
    ca = tmp_path / "other" / "ca.crt"
    write_config({"server_url": "https://h:1", "ca_cert": str(ca)})
    assert load_config(tmp_path).ca_cert == ca


def test_utf8_bom_accepted(tmp_path):
    (tmp_path / "config.json").write_text('{"server_url": "https://h:1", "ca_cert": "ca.crt"}', encoding="utf-8-sig")
    assert load_config(tmp_path).health_interval == 30.0


def test_missing_server_url_is_reported(tmp_path, write_config):
    write_config({"ca_cert": "ca.crt"})
    with pytest.raises(ConfigError, match="server_url"):
        load_config(tmp_path)


def test_http_url_rejected(tmp_path, write_config):
    write_config({"server_url": "http://h:1", "ca_cert": "ca.crt"})
    with pytest.raises(ConfigError, match="server_url"):
        load_config(tmp_path)


def test_bad_interval_rejected(tmp_path, write_config):
    write_config({"server_url": "https://h:1", "ca_cert": "ca.crt", "health_interval": 0})
    with pytest.raises(ConfigError, match="health_interval"):
        load_config(tmp_path)


def test_missing_file_is_reported(tmp_path):
    with pytest.raises(ConfigError, match="config.json"):
        load_config(tmp_path)


def test_invalid_json_is_reported(tmp_path):
    (tmp_path / "config.json").write_text("{", encoding="utf-8")
    with pytest.raises(ConfigError, match="JSON"):
        load_config(tmp_path)


def test_custom_ipc_port(tmp_path, write_config):
    write_config({"server_url": "https://h:1", "ca_cert": "ca.crt", "ipc_port": 50000})
    assert load_config(tmp_path).ipc_port == 50000


@pytest.mark.parametrize("port", [0, 70000, "47800", 1.5, True])
def test_bad_ipc_port_rejected(tmp_path, write_config, port):
    write_config({"server_url": "https://h:1", "ca_cert": "ca.crt", "ipc_port": port})
    with pytest.raises(ConfigError, match="ipc_port"):
        load_config(tmp_path)


def test_policy_public_key_defaults_to_data_dir(tmp_path, write_config):
    write_config({"server_url": "https://h:1", "ca_cert": "ca.crt"})
    assert load_config(tmp_path).policy_public_key == tmp_path / "policy_public.pem"


def test_policy_public_key_from_config(tmp_path, write_config):
    write_config({"server_url": "https://h:1", "ca_cert": "ca.crt", "policy_public_key": "keys/p.pem"})
    assert load_config(tmp_path).policy_public_key == tmp_path / "keys" / "p.pem"


@pytest.mark.parametrize("value", ["", 5, None])
def test_bad_policy_public_key_rejected(tmp_path, write_config, value):
    write_config({"server_url": "https://h:1", "ca_cert": "ca.crt", "policy_public_key": value})
    with pytest.raises(ConfigError, match="policy_public_key"):
        load_config(tmp_path)
