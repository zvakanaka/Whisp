conf_data = configuration_data()
conf_data.set('bindir', join_paths(get_option('prefix'), get_option('bindir')))

configure_file(
  input: 'io.github.tanaybhomia.Whisp.desktop.in',
  output: 'io.github.tanaybhomia.Whisp.desktop',
  configuration: conf_data,
  install: true,
  install_dir: get_option('datadir') / 'applications'
)


install_data('io.github.tanaybhomia.Whisp.metainfo.xml',
  install_dir: get_option('datadir') / 'metainfo'
)

install_data('icons/io.github.tanaybhomia.Whisp.svg',
  install_dir: get_option('datadir') / 'icons/hicolor/scalable/apps'
)

install_data('icons/io.github.tanaybhomia.Whisp-symbolic.svg',
  install_dir: get_option('datadir') / 'icons/hicolor/symbolic/apps'
)

install_data('icons/io.github.tanaybhomia.Whisp-pin-symbolic.svg',
  install_dir: get_option('datadir') / 'icons/hicolor/symbolic/apps'
)
