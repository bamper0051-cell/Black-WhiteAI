// neon_text_field.dart — Neon styled text input widget

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/neon_theme.dart';

class NeonTextField extends StatelessWidget {
  final TextEditingController controller;
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

  const NeonTextField({
    super.key,
    required this.controller,
    required this.label,
    this.hint         = '',
    this.prefixIcon,
    this.suffixIcon,
    this.obscureText  = false,
    this.keyboardType,
    this.maxLines     = 1,
    this.validator,
    this.onChanged,
    this.color        = NeonColors.cyan,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: GoogleFonts.jetBrainsMono(
            color: color.withOpacity(0.8),
            fontSize: 9,
            fontWeight: FontWeight.w700,
            letterSpacing: 2,
          ),
        ),
        const SizedBox(height: 6),
        TextFormField(
          controller:  controller,
          obscureText: obscureText,
          keyboardType: keyboardType,
          maxLines:    maxLines,
          validator:   validator,
          onChanged:   onChanged,
          style: GoogleFonts.jetBrainsMono(
            color: NeonColors.textPrimary,
            fontSize: 13,
          ),
          decoration: InputDecoration(
            hintText:   hint,
            hintStyle:  GoogleFonts.jetBrainsMono(
              color: NeonColors.textDisabled,
              fontSize: 12,
            ),
            prefixIcon: prefixIcon != null
                ? Icon(prefixIcon, color: color.withOpacity(0.6), size: 18)
                : null,
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
          ),
        ),
      ],
    );
  }
}
