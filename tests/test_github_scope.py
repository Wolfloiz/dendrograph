"""Um token amplia o que se vê da própria conta, nunca troca a conta pedida.

Os dois defeitos aqui foram encontrados na validação do MVP contra uma conta
real: `discover` ignorava o argumento `account` quando havia token, e o clone
nunca recebia credencial nenhuma.
"""

import unittest

from collectors.git import github, plumbing


class FakeRequest:
    """Responde ao endpoint pedido e registra quais URLs foram visitadas."""

    def __init__(self, login="wolfloiz", repositories=None):
        self.login = login
        self.repositories = repositories or []
        self.urls = []

    def __call__(self, url, token=None):
        self.urls.append(url)
        if url.endswith("/user"):
            return {"login": self.login}, {}
        if "page=1" in url:
            return self.repositories, {}
        return [], {}

    @property
    def repository_path(self):
        return next(u for u in self.urls if "repos" in u)


def repository(name="thing", full_name="wolfloiz/thing"):
    return {
        "name": name,
        "full_name": full_name,
        "clone_url": f"https://github.com/{full_name}.git",
        "html_url": f"https://github.com/{full_name}",
        "private": False,
        "fork": False,
        "description": None,
        "pushed_at": None,
    }


class DiscoveryStaysOnTheRequestedAccount(unittest.TestCase):
    def test_a_token_for_another_account_does_not_redirect_to_your_own(self):
        # O defeito: `dendro scan github:tinygrad` com um token no ambiente
        # varria a conta do próprio Author e trazia os privados dela junto.
        request = FakeRequest(login="wolfloiz", repositories=[repository()])
        found = github.discover("tinygrad", token="t", request=request)
        self.assertIn("/users/tinygrad/repos", request.repository_path)
        self.assertNotIn("/user/repos", request.repository_path)
        self.assertFalse(found.account_is_authenticated)

    def test_your_own_account_still_reaches_your_private_repositories(self):
        request = FakeRequest(login="wolfloiz", repositories=[repository()])
        found = github.discover("wolfloiz", token="t", request=request)
        self.assertIn("/user/repos", request.repository_path)
        self.assertTrue(found.account_is_authenticated)

    def test_the_login_comparison_ignores_case(self):
        request = FakeRequest(login="Wolfloiz", repositories=[repository()])
        github.discover("wolfloiz", token="t", request=request)
        self.assertIn("/user/repos", request.repository_path)

    def test_an_unusable_token_falls_back_to_the_public_endpoint(self):
        class Failing(FakeRequest):
            def __call__(self, url, token=None):
                if url.endswith("/user"):
                    raise github.RateLimited()
                return super().__call__(url, token)

        request = Failing(repositories=[repository()])
        found = github.discover("tinygrad", token="t", request=request)
        self.assertIn("/users/tinygrad/repos", request.repository_path)
        self.assertFalse(found.account_is_authenticated)

    def test_without_a_token_the_public_endpoint_is_used_and_user_is_never_called(self):
        request = FakeRequest(repositories=[repository()])
        github.discover("tinygrad", request=request)
        self.assertIn("/users/tinygrad/repos", request.repository_path)
        self.assertFalse([u for u in request.urls if u.endswith("/user")])


class TheTokenNeverTravelsWhereItCanBeRead(unittest.TestCase):
    TOKEN = "ghp_sekrit_do_not_leak"

    def _clone(self, url):
        calls = {}
        real = plumbing.subprocess.run

        def capture(args, **kwargs):
            calls["argv"] = args
            calls["env"] = kwargs.get("env") or {}
            return real(["false"], capture_output=True, text=True)

        plumbing.subprocess.run = capture
        try:
            with self.assertRaises(plumbing.GitError) as caught:
                plumbing.clone(url, "/tmp/dendro-never-created", token=self.TOKEN)
        finally:
            plumbing.subprocess.run = real
        calls["error"] = str(caught.exception)
        return calls

    def test_the_token_is_not_in_the_command_line(self):
        calls = self._clone("https://github.com/wolfloiz/thing.git")
        self.assertNotIn(self.TOKEN, " ".join(calls["argv"]))

    def test_the_token_is_not_in_the_error_message(self):
        # A mensagem de GitError repete a linha de comando e vai para o
        # relatório da varredura, que o Author lê e pode colar em outro lugar.
        calls = self._clone("https://github.com/wolfloiz/thing.git")
        self.assertNotIn(self.TOKEN, calls["error"])

    def test_the_token_reaches_git_through_the_environment(self):
        calls = self._clone("https://github.com/wolfloiz/thing.git")
        self.assertEqual(calls["env"].get(plumbing.TOKEN_VARIABLE), self.TOKEN)
        self.assertIn("credential.helper=" + plumbing.CREDENTIAL_HELPER, calls["argv"])

    def test_without_a_token_no_credential_helper_is_configured(self):
        real = plumbing.subprocess.run
        seen = {}

        def capture(args, **kwargs):
            seen["argv"] = args
            seen["env"] = kwargs.get("env") or {}
            return real(["false"], capture_output=True, text=True)

        plumbing.subprocess.run = capture
        try:
            with self.assertRaises(plumbing.GitError):
                plumbing.clone("https://example.invalid/x.git", "/tmp/dendro-never")
        finally:
            plumbing.subprocess.run = real
        self.assertNotIn("credential.helper", " ".join(seen["argv"]))
        self.assertNotIn(plumbing.TOKEN_VARIABLE, seen["env"])


if __name__ == "__main__":
    unittest.main()
