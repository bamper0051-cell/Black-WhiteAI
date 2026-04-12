"""
llm_client.py — загружает реализацию из fish_v2_merged/
"""
import importlib.util, os, sys

_src = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    'fish_v2_merged', 'llm_client.py')
_spec = importlib.util.spec_from_file_location('_llm_client_impl', _src)
_mod  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

call_llm             = _mod.call_llm
call_llm_full        = _mod.call_llm_full
test_connection      = _mod.test_connection
check_provider       = _mod.check_provider
check_all_providers  = _mod.check_all_providers
format_check_results = _mod.format_check_results

# Export _PROVIDER_KEY_MAP so bot.py can import it
try:
    _PROVIDER_KEY_MAP = _mod._PROVIDER_KEY_MAP
except AttributeError:
    # Fallback если нет в реализации
    _PROVIDER_KEY_MAP = {
        'openai':      'OPENAI_API_KEY',
        'anthropic':   'ANTHROPIC_API_KEY',
        'claude':      'ANTHROPIC_API_KEY',
        'gemini':      'GEMINI_API_KEY',
        'mistral':     'MISTRAL_API_KEY',
        'deepseek':    'DEEPSEEK_API_KEY',
        'groq':        'GROQ_API_KEY',
        'together':    'TOGETHER_API_KEY',
        'fireworks':   'FIREWORKS_API_KEY',
        'cerebras':    'CEREBRAS_API_KEY',
        'sambanova':   'SAMBANOVA_API_KEY',
        'novita':      'NOVITA_API_KEY',
        'deepinfra':   'DEEPINFRA_API_KEY',
        'openrouter':  'OPENROUTER_API_KEY',
        'xai':         'XAI_API_KEY',
    }
