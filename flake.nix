{
  description = "IPTV Manager — HavenOS fork (test environment)";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;

      sakee =
        pkgs:
        pkgs.python3Packages.buildPythonPackage rec {
          pname = "sakee";
          version = "0.1.9";

          src = pkgs.python3Packages.fetchPypi {
            inherit pname version;
            hash = "sha256-LQPEVXphtTWsV6tRebZcMs1eaperZBbQJ4MfHdewz8g=";
          };

          format = "setuptools";
          doCheck = false;
          pythonImportsCheck = [ "sakee" ];

          meta = {
            homepage = "https://github.com/retrospect-addon/kodi.emulator.ascii";
            description = "SAKÉ — Kodi Python add-on debug/development stubs";
            license = pkgs.lib.licenses.gpl3Only;
          };
        };

      testPython =
        pkgs:
        pkgs.python3.withPackages (
          ps: with ps; [
            (sakee pkgs)
            pytest
            pytest-cov
            pytest-timeout
            python-dateutil
            lxml
            polib
            mock
            pylint
          ]
        );
    in
    {
      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python = testPython pkgs;
        in
        {
          default = pkgs.mkShell {
            packages = [ python ];
            shellHook = ''
              echo "IPTV Manager test shell"
              echo "  KODI_HOME=tests/home KODI_INTERACTIVE=0 pytest -q tests"
              echo "  (run from a directory named service.iptv.manager: sakee uses its basename as addon id)"
            '';
          };
        }
      );

      checks = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          tests = pkgs.runCommand "iptv-manager-tests" {
            nativeBuildInputs = [ (testPython pkgs) ];
          } ''
            mkdir -p test
            cp -r ${self} test/service.iptv.manager
            chmod -R u+w test/service.iptv.manager
            cd test/service.iptv.manager

            export KODI_HOME="$PWD/tests/home"
            export KODI_INTERACTIVE=0
            pytest -q tests

            touch $out
          '';
        }
      );
    };
}
