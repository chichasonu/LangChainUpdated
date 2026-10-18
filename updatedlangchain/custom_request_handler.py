# custom_request_handler.py
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.context import ServerCallContext
from a2a.types.a2a_pb2 import SendMessageRequest, Task, Message
import logging

logger = logging.getLogger(__name__)

class CustomRequestHandler(DefaultRequestHandler):
    """
    Custom request handler that removes task history after processing.
    """
    
    async def on_message_send(
        self, 
        params: SendMessageRequest, 
        context: ServerCallContext
    ) -> Task | Message:
        """Override message/send to remove history after processing."""
        logger.info(f"Processing message for task: {params}")
        
        # Call the parent implementation to process the message
        result = await super().on_message_send(params, context)

        # logger.info(f"Result: {result}")
        
        # If result is a Task, remove its history
        if isinstance(result, Task):
            logger.info(f"Removing history from task: {result.id}")
            
            # Clear the history field
            result.ClearField('history')
            
            # Re-save the task without history to the task store
            await self.task_store.save(result, context)
            
            logger.info(f"Task {result.id} saved without history")
        
        return result