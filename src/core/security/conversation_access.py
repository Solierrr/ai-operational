class ConversationAccessDenied(Exception):
    """A conversa é de outro usuário, ou o usuário não pôde ser identificado."""


def thread_key(conversation_id: str) -> str:
    """Chave da thread no checkpointer. O ai-assistant delega com o próprio id de
    conversa e os dois serviços guardam checkpoints na mesma coleção: sem o prefixo, os
    grafos escreveriam na mesma thread."""
    return f"operational:{conversation_id}"
