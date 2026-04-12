// neon_text_field.dart — Neon styled text input widget

import 'package:flutter/material.dart';
import '../theme/neon_theme.dart';

class NeonTextField extends StatelessWidget {
  final TextEditingController controller;
<<<<<<< HEAD
  final String  label;
  final String  hint;
  final IconData? prefixIcon;
  final Widget?   suffixIcon;
  final bool    obscureText;
  final TextInputType? keyboardType;
  final int     maxLines;
  final String? Function(String?)? validator;
  final void Function(String)? onChanged;
  final Color   color;
=======
  final String label;
  final String hint;
  final IconData? prefixIcon;
  final Widget? suffixIcon;
  final bool obscureText;
  final TextInputType? keyboardType;
  final int maxLines;
  final String? Function(String?)? validator;
  final void Function(String)? onChanged;
  final Color color;
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999

  const NeonTextField({
    super.key,
    required this.controller,
    required this.label,
<<<<<<< HEAD
    this.hint         = '',
    this.prefixIcon,
    this.suffixIcon,
    this.obscureText  = false,
    this.keyboardType,
    this.maxLines     = 1,
    this.validator,
    this.onChanged,
    this.color        = NeonColors.cyan,
=======
    this.hint = '',
    this.prefixIcon,
    this.suffixIcon,
    this.obscureText = false,
    this.keyboardType,
    this.maxLines = 1,
    this.validator,
    this.onChanged,
    this.color = NeonColors.cyan,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
<<<<<<< HEAD
            color:       color.withOpacity(0.8),
            fontFamily: 'JetBrainsMono',
            fontSize:   9,
=======
            color: color.withOpacity(0.8),
            fontFamily: 'Orbitron',
            fontSize: 9,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
            fontWeight: FontWeight.w700,
            letterSpacing: 2,
          ),
        ),
        const SizedBox(height: 6),
        TextFormField(
<<<<<<< HEAD
          controller:  controller,
          obscureText: obscureText,
          keyboardType: keyboardType,
          maxLines:    maxLines,
          validator:   validator,
          onChanged:   onChanged,
          style: const TextStyle(
            color:      NeonColors.textPrimary,
            fontFamily: 'JetBrainsMono',
            fontSize:   13,
          ),
          decoration: InputDecoration(
            hintText:   hint,
            hintStyle:  TextStyle(
              color:      NeonColors.textDisabled,
              fontFamily: 'JetBrainsMono',
              fontSize:   12,
=======
          controller: controller,
          obscureText: obscureText,
          keyboardType: keyboardType,
          maxLines: maxLines,
          validator: validator,
          onChanged: onChanged,
          style: const TextStyle(
            color: NeonColors.textPrimary,
            fontFamily: 'JetBrainsMono',
            fontSize: 13,
          ),
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: const TextStyle(
              color: NeonColors.textDisabled,
              fontFamily: 'JetBrainsMono',
              fontSize: 12,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
            ),
            prefixIcon: prefixIcon != null
                ? Icon(prefixIcon, color: color.withOpacity(0.6), size: 18)
                : null,
<<<<<<< HEAD
            suffixIcon:    suffixIcon,
            filled:        true,
            fillColor:     NeonColors.bgCard,
            contentPadding: const EdgeInsets.symmetric(
                horizontal: 14, vertical: 12),
            border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: BorderSide(color: color.withOpacity(0.3))),
            enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: BorderSide(color: color.withOpacity(0.3))),
            focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: BorderSide(color: color, width: 1.5)),
            errorBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: const BorderSide(color: NeonColors.pink)),
=======
            suffixIcon: suffixIcon,
            filled: true,
            fillColor: NeonColors.bgCard,
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 14,
              vertical: 12,
            ),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: BorderSide(color: color.withOpacity(0.3)),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: BorderSide(color: color.withOpacity(0.3)),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: BorderSide(color: color, width: 1.5),
            ),
            errorBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: const BorderSide(color: NeonColors.pink),
            ),
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
          ),
        ),
      ],
    );
  }
}
