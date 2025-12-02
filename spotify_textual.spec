Name: Spotify_textual
Version: 1
Release: 1
Summary: A spotify client in terminal
License: MIT
Requires: systemd

%description
A spotify client in terminal

%build
pyinstaller --onefile %{_sourcedir}/main.py

%install
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_unitdir}
install -m 755 dist/main %{buildroot}%{_bindir}/spotify_textual
install -m 755 %{_sourcedir}/spotfy_textual.service %{buildroot}%{_unitdir}/spotify_textual.service

%files
%{_bindir}/spotify_textual
%{_unitdir}/spotify_textual.service
