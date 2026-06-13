import 'package:flutter/material.dart';
import '../constantes/colores.dart';

ThemeData temaOscuro() => ThemeData(
  useMaterial3: true,
  brightness: Brightness.dark,
  scaffoldBackgroundColor: kFondoOscuro,
  colorScheme: ColorScheme.dark(
    primary:   kPrimario,
    surface:   kSuperficieOscura,
    onPrimary: Colors.white,
    error:     kPeligro,
  ),
  cardColor: kSuperficieOscura,
  dividerColor: kBordeOscuro,
  textTheme: _textTheme(kTextoOscuro),
  appBarTheme: AppBarTheme(
    backgroundColor: kSuperficieOscura,
    foregroundColor: kTextoOscuro,
    elevation: 0,
    surfaceTintColor: Colors.transparent,
  ),
  navigationRailTheme: NavigationRailThemeData(
    backgroundColor: kSuperficieOscura,
    selectedIconTheme: IconThemeData(color: kPrimario),
    unselectedIconTheme: IconThemeData(color: kTexto2Oscuro),
    selectedLabelTextStyle: TextStyle(color: kPrimario, fontWeight: FontWeight.w600),
    unselectedLabelTextStyle: TextStyle(color: kTexto2Oscuro),
  ),
);

ThemeData temaClaro() => ThemeData(
  useMaterial3: true,
  brightness: Brightness.light,
  scaffoldBackgroundColor: kFondoClaro,
  colorScheme: ColorScheme.light(
    primary:   kPrimario,
    surface:   kSuperficieClara,
    onPrimary: Colors.white,
    error:     kPeligro,
  ),
  cardColor: kSuperficieClara,
  dividerColor: kBordeClaro,
  textTheme: _textTheme(kTextoClaro),
  appBarTheme: AppBarTheme(
    backgroundColor: kSuperficieClara,
    foregroundColor: kTextoClaro,
    elevation: 0,
    surfaceTintColor: Colors.transparent,
  ),
);

TextTheme _textTheme(Color color) => TextTheme(
  bodyMedium: TextStyle(color: color),
  bodySmall:  TextStyle(color: color.withAlpha(160)),
  titleMedium: TextStyle(color: color, fontWeight: FontWeight.w600),
);
