import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final temaProvider = StateProvider<ThemeMode>((ref) => ThemeMode.dark);
