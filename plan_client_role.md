# Client Role Implementation Plan

## Overview
Add a new "Client" role to the system that allows users to assign chatbots to clients. Clients will have access only to assigned chatbots and cannot create or manage chatbots themselves. They will only see the chat interface.

**Note:** This implementation adds Client role while preserving existing User and Super User functionality.

## Database Schema Changes

### 1. Update User_Auth_Table (db_service.py)
**File:** `backend/db_service.py`
**Lines:** 40
**Change:** Update role choices
```python
# Current
role = StringField(required=True, choices=['User', 'Super User'])

# New
role = StringField(required=True, choices=['User', 'Super User', 'Client'])
```

### 2. Add New Collection - ChatbotClientMapper
**File:** `backend/db_service.py`
**Location:** After ChatbotDocumentsMapper class (after line 342)
**Action:** Add new collection

```python
class ChatbotClientMapper(Document):
    """Mapping table between ChatBots and Client Users"""
    chatbot = ReferenceField(ChatBots, required=True)
    client = ReferenceField(User_Auth_Table, required=True)  # Must have role='Client'
    assigned_by = ReferenceField(User_Auth_Table, required=True)  # The User who assigned it (role='User')
    assigned_at = DateTimeField(required=True)
    is_active = BooleanField(default=True)  # Allow revoking access
    
    meta = {
        'collection': 'chatbot_client_mapper',
        'indexes': [
            {'fields': [('chatbot', 1), ('client', 1)], 'unique': True},
            {'fields': ['client']},
            {'fields': ['assigned_by']},
            {'fields': ['is_active']}
        ]
    }
    
    def __str__(self) -> str:
        return f"ChatbotClientMapper(chatbot={self.chatbot}, client={self.client}, assigned_by={self.assigned_by}, is_active={self.is_active})"
```

### 3. Add Database Service Functions
**File:** `backend/db_service.py`
**Location:** End of file, before __main__ section
**Action:** Add new functions

```python
def assign_chatbot_to_client(chatbot_id: str, client_id: str, assigned_by_user_id: str) -> ChatbotClientMapper:
    """Assign a chatbot to a client"""
    try:
        # Validate entities exist
        chatbot = ChatBots.objects(id=chatbot_id).first()
        client = User_Auth_Table.objects(id=client_id, role='Client').first()
        assigned_by = User_Auth_Table.objects(id=assigned_by_user_id).first()
        
        if not all([chatbot, client, assigned_by]):
            raise ValueError("Invalid chatbot, client, or assigner")
        
        # Check if assignment already exists
        existing = ChatbotClientMapper.objects(chatbot=chatbot, client=client).first()
        if existing:
            existing.is_active = True
            existing.assigned_at = datetime.now()
            existing.save()
            return existing
        
        # Create new assignment
        assignment = ChatbotClientMapper(
            chatbot=chatbot,
            client=client,
            assigned_by=assigned_by,
            assigned_at=datetime.now(),
            is_active=True
        )
        assignment.save()
        return assignment
        
    except Exception as e:
        print(f"Error assigning chatbot to client: {e}")
        raise

def revoke_chatbot_from_client(chatbot_id: str, client_id: str) -> bool:
    """Revoke a chatbot assignment from a client"""
    try:
        assignment = ChatbotClientMapper.objects(
            chatbot=chatbot_id, 
            client=client_id
        ).first()
        
        if assignment:
            assignment.is_active = False
            assignment.save()
            return True
        return False
        
    except Exception as e:
        print(f"Error revoking chatbot from client: {e}")
        return False

def get_client_assigned_chatbots(client_id: str) -> List[ChatBots]:
    """Get all chatbots assigned to a client"""
    try:
        assignments = ChatbotClientMapper.objects(
            client=client_id, 
            is_active=True
        )
        return [assignment.chatbot for assignment in assignments]
        
    except Exception as e:
        print(f"Error getting client assigned chatbots: {e}")
        return []

def get_chatbot_clients(chatbot_id: str) -> List[User_Auth_Table]:
    """Get all clients assigned to a chatbot"""
    try:
        assignments = ChatbotClientMapper.objects(
            chatbot=chatbot_id, 
            is_active=True
        )
        return [assignment.client for assignment in assignments]
        
    except Exception as e:
        print(f"Error getting chatbot clients: {e}")
        return []

def validate_client_chatbot_access(client_id: str, chatbot_id: str) -> bool:
    """Validate if a client has access to a specific chatbot"""
    try:
        assignment = ChatbotClientMapper.objects(
            client=client_id,
            chatbot=chatbot_id,
            is_active=True
        ).first()
        return assignment is not None
        
    except Exception as e:
        print(f"Error validating client chatbot access: {e}")
        return False

def get_available_clients() -> List[User_Auth_Table]:
    """Get all users with Client role"""
    try:
        return User_Auth_Table.objects(role='Client')
    except Exception as e:
        print(f"Error getting available clients: {e}")
        return []
```

## Backend API Changes

### 1. Update API Models
**File:** `backend/api_models.py`
**Lines:** 48-52
**Change:** Update UserRole enum

```python
# Current
class UserRole(str, Enum):
    """Enumeration for user roles"""
    USER = "User"
    SUPER_USER = "Super User"

# New
class UserRole(str, Enum):
    """Enumeration for user roles"""
    USER = "User"
    SUPER_USER = "Super User"
    CLIENT = "Client"
```

### 2. Add New Response Models
**File:** `backend/api_models.py`
**Location:** After existing response models
**Action:** Add new models

```python
class EmailAssignmentRequest(BaseModel):
    """Request model for assigning chatbot to client by email"""
    chatbot_id: str = Field(..., description="Chatbot ID")
    client_email: str = Field(..., description="Client email address")

class EmailAssignmentResponse(BaseModel):
    """Response model for email-based chatbot assignment"""
    message: str = Field(..., description="Success message")
    client_email: str = Field(..., description="Client email")
    new_client: bool = Field(..., description="Whether a new client was created")
    assignment_id: str = Field(..., description="Assignment ID")

class ChatbotClientInfo(BaseModel):
    """Information about a client assigned to a chatbot"""
    client_id: str
    user_name: str
    first_name: str
    last_name: str
    email: str
    assigned_at: datetime
    is_active: bool
```

### 3. Add New API Endpoints
**File:** `backend/main.py`
**Location:** After existing chatbot endpoints
**Action:** Add new endpoints

```python
@app.post("/api/assign-chatbot-by-email", response_model=EmailAssignmentResponse)
async def assign_chatbot_by_email(
    request: EmailAssignmentRequest,
    current_user: User_Auth_Table = Depends(get_current_user)
):
    """Assign chatbot to client by email - creates client if doesn't exist (Users and Super Users only)"""
    if current_user.role not in ['User', 'Super User']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Users and Super Users can assign chatbots to clients"
        )
    
    try:
        # Find or create client
        client = User_Auth_Table.objects(email=request.client_email).first()
        new_client_created = False
        
        if not client:
            # Create new client account
            temp_password = generate_random_password()
            client = User_Auth_Table(
                user_name=request.client_email.split('@')[0],  # Use email prefix as username
                email=request.client_email,
                password=get_password_hash(temp_password),
                first_name="",  # To be filled by client
                last_name="", 
                role="Client",
                created_at=datetime.now()
            )
            client.save()
            new_client_created = True
            
            # Send welcome email with credentials
            send_welcome_email(request.client_email, temp_password)
            
        elif client.role != 'Client':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign chatbot to Users - only Clients are allowed"
            )
        
        # Check if already assigned
        from db_service import ChatbotClientMapper
        existing = ChatbotClientMapper.objects(
            chatbot=request.chatbot_id, 
            client=client.id,
            is_active=True
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Chatbot already assigned to {request.client_email}"
            )
        
        # Assign chatbot
        from db_service import assign_chatbot_to_client
        assignment = assign_chatbot_to_client(
            request.chatbot_id, 
            str(client.id), 
            str(current_user.id)
        )
        
        return EmailAssignmentResponse(
            message=f"Chatbot assigned to {request.client_email}",
            client_email=request.client_email,
            new_client=new_client_created,
            assignment_id=str(assignment.id)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign chatbot by email: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to assign chatbot: {str(e)}"
        )

@app.delete("/api/revoke-chatbot-from-client")
async def revoke_chatbot_from_client(
    chatbot_id: str,
    client_email: str,
    current_user: User_Auth_Table = Depends(get_current_user)
):
    """Revoke a chatbot assignment from a client by email"""
    if current_user.role not in ['User', 'Super User']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Users and Super Users can revoke chatbot assignments"
        )
    
    try:
        # Find client by email
        client = User_Auth_Table.objects(email=client_email).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client with email {client_email} not found"
            )
        
        from db_service import revoke_chatbot_from_client
        success = revoke_chatbot_from_client(chatbot_id, str(client.id))
        
        if success:
            return {"message": f"Chatbot assignment revoked from {client_email}"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke chatbot from client: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to revoke chatbot assignment: {str(e)}"
        )

@app.get("/api/chatbot-assignments/{chatbot_id}", response_model=List[ChatbotClientInfo])
async def get_chatbot_assignments(
    chatbot_id: str,
    current_user: User_Auth_Table = Depends(get_current_user)
):
    """Get all clients assigned to a chatbot"""
    if current_user.role not in ['User', 'Super User']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Users and Super Users can view chatbot assignments"
        )
    
    try:
        from db_service import get_chatbot_clients
        clients = get_chatbot_clients(chatbot_id)
        
        return [
            ChatbotClientInfo(
                client_id=str(client.id),
                user_name=client.user_name,
                first_name=client.first_name,
                last_name=client.last_name,
                email=client.email,
                assigned_at=datetime.now(),  # You'd get this from the assignment
                is_active=True
            )
            for client in clients
        ]
        
    except Exception as e:
        logger.error(f"Failed to get chatbot assignments: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get chatbot assignments: {str(e)}"
        )

@app.get("/api/my-assigned-chatbots", response_model=List[ChatbotDetailResponse])
async def get_my_assigned_chatbots(
    current_user: User_Auth_Table = Depends(get_current_user)
):
    """Get chatbots assigned to the current client"""
    if current_user.role != 'Client':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Clients can access assigned chatbots"
        )
    
    try:
        from db_service import get_client_assigned_chatbots
        chatbots = get_client_assigned_chatbots(str(current_user.id))
        
        return [
            ChatbotDetailResponse(
                id=str(chatbot.id),
                name=chatbot.name,
                description=chatbot.description,
                embedding_model=chatbot.embedding_model,
                chunking_method=chatbot.chunking_method,
                date_created=chatbot.date_created,
                namespace=chatbot.namespace
            )
            for chatbot in chatbots
        ]
        
    except Exception as e:
        logger.error(f"Failed to get assigned chatbots: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get assigned chatbots: {str(e)}"
        )

# Helper functions for email-based assignment
def generate_random_password(length: int = 12) -> str:
    """Generate a random temporary password"""
    import string
    import secrets
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def send_welcome_email(email: str, temp_password: str, chatbot_name: str = ""):
    """Send welcome email to new client with login instructions"""
    try:
        subject = f"Welcome! You've been given access to {'a chatbot' if not chatbot_name else chatbot_name}"
        body = f"""
Hello!

You've been given access to {'a chatbot' if not chatbot_name else f'the chatbot "{chatbot_name}"'}. 

Here are your login credentials:
Email: {email}
Temporary Password: {temp_password}

Please log in and change your password as soon as possible.

Login at: {os.getenv('FRONTEND_URL', 'http://localhost:3000')}/auth

Best regards,
Your Chatbot Team
        """
        
        # TODO: Implement actual email sending using your preferred service
        # Example: SendGrid, AWS SES, etc.
        logger.info(f"Welcome email would be sent to {email}")
        print(f"Welcome email for {email}: {body}")
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to {email}: {e}")
        # Don't fail the assignment if email fails
        pass
```

### 4. Update Existing Endpoints with Role-Based Access
**File:** `backend/main.py`
**Location:** Existing chatbot endpoints
**Action:** Modify access control

#### Update Get Chatbots Endpoint
**Lines:** Around line 226 (where getUserChatbots is implemented)
```python
# Update the /chatbots endpoint to handle role-based filtering
@app.get("/chatbots", response_model=List[ChatbotDetailResponse])
async def get_user_chatbots(current_user: User_Auth_Table = Depends(get_current_user)):
    """Get chatbots for current user based on role"""
    try:
        if current_user.role == 'Client':
            # Clients see only assigned chatbots
            from db_service import get_client_assigned_chatbots
            chatbots = get_client_assigned_chatbots(str(current_user.id))
        elif current_user.role == 'User':
            # Users see owned chatbots
            chatbots = ChatBots.objects(user_id=current_user.id)
        elif current_user.role == 'Super User':
            # Super Users see all chatbots
            chatbots = ChatBots.objects()
        else:
            # Invalid role
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid user role"
            )
        
        # Return chatbot details...
```

#### Add Access Validation to Conversation Endpoints
**Location:** All conversation and session endpoints
**Action:** Add client access validation

```python
# Add this helper function
def validate_chatbot_access(user: User_Auth_Table, chatbot_id: str) -> bool:
    """Validate if user has access to chatbot based on their role"""
    if user.role in ['User', 'Super User']:
        # Check if they own the chatbot (or Super User has access to all)
        if user.role == 'Super User':
            return True  # Super Users have access to all chatbots
        chatbot = ChatBots.objects(id=chatbot_id, user_id=user.id).first()
        return chatbot is not None
    elif user.role == 'Client':
        # Check if chatbot is assigned to them
        from db_service import validate_client_chatbot_access
        return validate_client_chatbot_access(str(user.id), chatbot_id)
    return False

# Use this function in all chatbot-related endpoints
```

## Frontend Changes

### 1. Update API Client
**File:** `front_end/src/utils/api.ts`
**Location:** After existing APIs
**Action:** Add new API functions

```typescript
// Add to existing APIs - Email-based client assignment
export const clientApi = {
    // Assign chatbot to client by email (creates client if doesn't exist)
    assignChatbotByEmail: (chatbotId: string, clientEmail: string) =>
        apiClient.post('/api/assign-chatbot-by-email', {
            chatbot_id: chatbotId,
            client_email: clientEmail
        }),

    // Revoke chatbot from client by email
    revokeChatbotFromClient: (chatbotId: string, clientEmail: string) =>
        apiClient.delete(`/api/revoke-chatbot-from-client?chatbot_id=${chatbotId}&client_email=${clientEmail}`),

    // Get chatbot assignments (returns list of clients with emails)
    getChatbotAssignments: (chatbotId: string) =>
        apiClient.get(`/api/chatbot-assignments/${chatbotId}`),

    // Get assigned chatbots (for clients)
    getMyAssignedChatbots: () =>
        apiClient.get('/api/my-assigned-chatbots'),
};

// Update chatbotApi.getUserChatbots to handle role-based results
```

### 2. Update User Auth Store
**File:** `front_end/src/stores/UserAuthStore.ts`
**Lines:** 6-10
**Action:** Update User interface

```typescript
interface User {
    name: string;
    email?: string;
    role?: 'User' | 'Super User' | 'Client';  // All three roles supported
}
```

### 3. Create Client Dashboard
**File:** `front_end/src/pages/ClientDashboard.tsx`
**Action:** Create new file

```typescript
import React, { useEffect, useState } from 'react';
import { clientApi } from '../utils/api';
import ChatComponent from '../components/ChatComponent';
import LoadedChatbotStore from '../stores/LoadedChatbotStore';
import ViewStore from '../stores/ViewStore';

interface AssignedChatbot {
    id: string;
    name: string;
    description: string;
    embedding_model: string;
    chunking_method: string;
    date_created: string;
    namespace: string;
}

const ClientDashboard: React.FC = () => {
    const [assignedChatbots, setAssignedChatbots] = useState<AssignedChatbot[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedChatbot, setSelectedChatbot] = useState<AssignedChatbot | null>(null);
    const { setLoadedChatbot } = LoadedChatbotStore();
    const { addError } = ViewStore();

    useEffect(() => {
        fetchAssignedChatbots();
    }, []);

    const fetchAssignedChatbots = async () => {
        try {
            const response = await clientApi.getMyAssignedChatbots();
            setAssignedChatbots(response);
            
            // Auto-select first chatbot if available
            if (response.length > 0 && !selectedChatbot) {
                handleChatbotSelect(response[0]);
            }
        } catch (error) {
            console.error('Failed to fetch assigned chatbots:', error);
            addError('Failed to load assigned chatbots');
        } finally {
            setLoading(false);
        }
    };

    const handleChatbotSelect = (chatbot: AssignedChatbot) => {
        setSelectedChatbot(chatbot);
        setLoadedChatbot(chatbot);
    };

    if (loading) {
        return (
            <div className="h-screen flex items-center justify-center">
                <div className="text-lg">Loading your assigned chatbots...</div>
            </div>
        );
    }

    if (assignedChatbots.length === 0) {
        return (
            <div className="h-screen flex items-center justify-center">
                <div className="text-center">
                    <h2 className="text-2xl font-semibold mb-4">No Chatbots Assigned</h2>
                    <p className="text-gray-600">
                        You don't have any chatbots assigned to you yet. 
                        Please contact your administrator.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="h-screen flex flex-col">
            {/* Header with chatbot selector */}
            <div className="bg-white border-b border-gray-200 p-4">
                <div className="flex items-center justify-between">
                    <h1 className="text-xl font-semibold">My Chatbots</h1>
                    <select
                        value={selectedChatbot?.id || ''}
                        onChange={(e) => {
                            const chatbot = assignedChatbots.find(c => c.id === e.target.value);
                            if (chatbot) handleChatbotSelect(chatbot);
                        }}
                        className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        {assignedChatbots.map(chatbot => (
                            <option key={chatbot.id} value={chatbot.id}>
                                {chatbot.name}
                            </option>
                        ))}
                    </select>
                </div>
                {selectedChatbot && (
                    <p className="text-sm text-gray-600 mt-2">
                        {selectedChatbot.description}
                    </p>
                )}
            </div>

            {/* Chat interface */}
            <div className="flex-1 p-4">
                {selectedChatbot ? (
                    <ChatComponent />
                ) : (
                    <div className="h-full flex items-center justify-center">
                        <div className="text-gray-500">Select a chatbot to start chatting</div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ClientDashboard;
```

### 4. Create Client Assignment Component
**File:** `front_end/src/components/AssignClientsModalComponent.tsx`
**Action:** Create new file

```typescript
import React, { useState, useEffect } from 'react';
import { Modal, Button, TextField, IconButton, Typography, List, ListItem } from '@mui/material';
import { Delete } from '@mui/icons-material';
import { clientApi } from '../utils/api';
import ViewStore from '../stores/ViewStore';

interface AssignedClient {
    client_id: string;
    user_name: string;
    first_name: string;
    last_name: string;
    email: string;
    assigned_at: string;
    is_active: boolean;
}

interface AssignClientsModalProps {
    open: boolean;
    onClose: () => void;
    chatbotId: string;
    chatbotName: string;
}

const AssignClientsModalComponent: React.FC<AssignClientsModalProps> = ({
    open,
    onClose,
    chatbotId,
    chatbotName
}) => {
    const [clientEmail, setClientEmail] = useState('');
    const [assignedClients, setAssignedClients] = useState<AssignedClient[]>([]);
    const [loading, setLoading] = useState(false);
    const [addingClient, setAddingClient] = useState(false);
    const { addSuccess, addError } = ViewStore();

    useEffect(() => {
        if (open) {
            fetchAssignedClients();
        }
    }, [open, chatbotId]);

    const fetchAssignedClients = async () => {
        setLoading(true);
        try {
            const assignments = await clientApi.getChatbotAssignments(chatbotId);
            setAssignedClients(assignments);
        } catch (error) {
            console.error('Failed to fetch assigned clients:', error);
            addError('Failed to load assigned clients');
        } finally {
            setLoading(false);
        }
    };

    const handleAddClient = async () => {
        if (!clientEmail.trim()) {
            addError('Please enter a valid email address');
            return;
        }

        setAddingClient(true);
        try {
            const response = await clientApi.assignChatbotByEmail(chatbotId, clientEmail.trim());
            
            if (response.new_client) {
                addSuccess(`New client created and chatbot assigned to ${clientEmail}. Welcome email sent.`);
            } else {
                addSuccess(`Chatbot assigned to existing client ${clientEmail}`);
            }
            
            setClientEmail('');
            await fetchAssignedClients(); // Refresh the list
        } catch (error: any) {
            console.error('Failed to assign chatbot:', error);
            addError(error.message || 'Failed to assign chatbot to client');
        } finally {
            setAddingClient(false);
        }
    };

    const handleRemoveClient = async (clientEmail: string) => {
        try {
            await clientApi.revokeChatbotFromClient(chatbotId, clientEmail);
            addSuccess(`Chatbot access revoked from ${clientEmail}`);
            await fetchAssignedClients(); // Refresh the list
        } catch (error: any) {
            console.error('Failed to revoke chatbot:', error);
            addError(error.message || 'Failed to revoke chatbot access');
        }
    };

    const isValidEmail = (email: string) => {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    };

    return (
        <Modal open={open} onClose={onClose}>
            <div className="fixed inset-0 flex items-center justify-center p-4">
                <div className="bg-white rounded-lg shadow-xl max-w-lg w-full max-h-[80vh] overflow-hidden">
                    <div className="p-6 border-b">
                        <Typography variant="h6">
                            Manage Client Access - {chatbotName}
                        </Typography>
                    </div>
                    
                    <div className="p-6 overflow-y-auto flex-1">
                        {/* Add new client section */}
                        <div className="mb-6">
                            <Typography variant="subtitle1" className="mb-3">
                                Add Client by Email
                            </Typography>
                            <div className="flex gap-2">
                                <TextField
                                    type="email"
                                    value={clientEmail}
                                    onChange={(e) => setClientEmail(e.target.value)}
                                    placeholder="Enter client email address"
                                    variant="outlined"
                                    size="small"
                                    fullWidth
                                    error={clientEmail.trim() !== '' && !isValidEmail(clientEmail)}
                                    helperText={
                                        clientEmail.trim() !== '' && !isValidEmail(clientEmail) 
                                            ? 'Please enter a valid email address' 
                                            : 'If client doesn\'t exist, a new account will be created'
                                    }
                                />
                                <Button
                                    onClick={handleAddClient}
                                    variant="contained"
                                    disabled={addingClient || !isValidEmail(clientEmail)}
                                    size="small"
                                >
                                    {addingClient ? 'Adding...' : 'Add'}
                                </Button>
                            </div>
                        </div>

                        {/* Currently assigned clients */}
                        <div>
                            <Typography variant="subtitle1" className="mb-3">
                                Currently Assigned Clients ({assignedClients.length})
                            </Typography>
                            
                            {loading ? (
                                <div className="text-center py-8">Loading...</div>
                            ) : assignedClients.length === 0 ? (
                                <div className="text-center py-8 text-gray-500">
                                    No clients assigned yet
                                </div>
                            ) : (
                                <List>
                                    {assignedClients.map(client => (
                                        <ListItem 
                                            key={client.client_id}
                                            className="flex items-center justify-between p-3 border rounded mb-2"
                                        >
                                            <div className="flex items-center">
                                                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center mr-3">
                                                    <span className="text-blue-600 font-medium">
                                                        {client.email[0].toUpperCase()}
                                                    </span>
                                                </div>
                                                <div>
                                                    <div className="font-medium">
                                                        {client.first_name && client.last_name 
                                                            ? `${client.first_name} ${client.last_name}`
                                                            : client.user_name
                                                        }
                                                    </div>
                                                    <div className="text-sm text-gray-500">
                                                        {client.email}
                                                    </div>
                                                    <div className="text-xs text-gray-400">
                                                        Assigned: {new Date(client.assigned_at).toLocaleDateString()}
                                                    </div>
                                                </div>
                                            </div>
                                            
                                            <IconButton
                                                onClick={() => handleRemoveClient(client.email)}
                                                color="error"
                                                size="small"
                                                title="Remove access"
                                            >
                                                <Delete />
                                            </IconButton>
                                        </ListItem>
                                    ))}
                                </List>
                            )}
                        </div>
                    </div>
                    
                    <div className="p-6 border-t flex justify-end">
                        <Button onClick={onClose}>
                            Close
                        </Button>
                    </div>
                </div>
            </div>
        </Modal>
    );
};

export default AssignClientsModalComponent;
```

### 5. Update Protected Route Component
**File:** `front_end/src/components/ProtectedRoute.tsx`
**Lines:** 17, 32-33, 37
**Action:** Fix missing functions and improve role checking

```typescript
import { useEffect, ReactNode } from 'react';
import UserAuthStore from '../stores/UserAuthStore';

interface ProtectedRouteProps {
    children: ReactNode;
    requiredPermission?: string;
    requiredRole?: 'User' | 'Super User' | 'Client';
    allowedRoles?: ('User' | 'Super User' | 'Client')[];
    fallback?: ReactNode;
}

const ProtectedRoute = ({ 
    children, 
    requiredPermission, 
    requiredRole,
    allowedRoles,
    fallback = <div>Access Denied</div> 
}: ProtectedRouteProps) => {
    const { user, isLoggedIn } = UserAuthStore();

    // Not logged in
    if (!isLoggedIn || !user) {
        return <div>Please log in to access this feature</div>;
    }

    // Check specific role
    if (requiredRole && user.role !== requiredRole) {
        return <>{fallback}</>;
    }

    // Check allowed roles
    if (allowedRoles && !allowedRoles.includes(user.role as any)) {
        return <>{fallback}</>;
    }

    return <>{children}</>;
};

export default ProtectedRoute;
```

### 6. Update Sidebar Component
**File:** `front_end/src/components/SidebarComponent.tsx`
**Lines:** Around 156 and 248
**Action:** Add client assignment option

```typescript
// Add after the existing Super User conditional (around line 156)
                {(user?.role === 'User' || user?.role === 'Super User') && (
                    <>
                        <button
                            onClick={handleExistingChatbotsClick}
                            className="w-full p-3 glass-effect rounded-lg text-white hover:bg-white/10 transition-colors"
                        >
                            <span className="material-symbols-outlined text-sm mr-2">smart_toy</span>
                            Choose Chatbot
                        </button>
                        <button
                            onClick={() => setAssignClientsModalOpen(true)}
                            className="w-full p-3 glass-effect rounded-lg text-white hover:bg-white/10 transition-colors"
                        >
                            <span className="material-symbols-outlined text-sm mr-2">group_add</span>
                            Assign to Clients
                        </button>
                    </>
                )}

// Add state and modal for client assignment
const [assignClientsModalOpen, setAssignClientsModalOpen] = useState(false);

// Add the modal component
{loadedChatbot && (
    <AssignClientsModalComponent
        open={assignClientsModalOpen}
        onClose={() => setAssignClientsModalOpen(false)}
        chatbotId={loadedChatbot.id}
        chatbotName={loadedChatbot.name}
    />
)}
```

### 7. Update Main App Routing
**File:** `front_end/src/App.tsx`
**Lines:** Around 31 and main return
**Action:** Add role-based routing

```typescript
// Update the role assignment (around line 31)
role: response.role || 'User',

// Update the main return to handle different role interfaces
return (
    <Router>
        <Routes>
            <Route path="/auth" element={<AuthPage />} />
            <Route 
                path="/" 
                element={
                    <ProtectedRoute allowedRoles={['User', 'Super User', 'Client']}>
                        {user?.role === 'Client' ? (
                            <ClientDashboard />
                        ) : (
                            <MainPage />
                        )}
                    </ProtectedRoute>
                } 
            />
        </Routes>
    </Router>
);
```

### 8. Update Manage Chatbots Modal
**File:** `front_end/src/components/ManageChatbotsModalComponent.tsx`
**Location:** In the chatbot actions section
**Action:** Add client assignment button

```typescript
// Add in the chatbot actions section (around where edit/delete buttons are)
{(user?.role === 'User' || user?.role === 'Super User') && (
    <button
        onClick={() => {
            setAssignClientsModalOpen(true);
            setSelectedChatbotForAssignment(chatbot);
        }}
        className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors text-sm"
    >
        Assign Clients
    </button>
)}

// Add state for assignment modal
const [assignClientsModalOpen, setAssignClientsModalOpen] = useState(false);
const [selectedChatbotForAssignment, setSelectedChatbotForAssignment] = useState(null);

// Add the modal
{selectedChatbotForAssignment && (
    <AssignClientsModalComponent
        open={assignClientsModalOpen}
        onClose={() => {
            setAssignClientsModalOpen(false);
            setSelectedChatbotForAssignment(null);
        }}
        chatbotId={selectedChatbotForAssignment.id}
        chatbotName={selectedChatbotForAssignment.name}
    />
)}
```

## Email-Based Assignment Workflow

### **User Experience:**
1. **User opens "Manage Client Access"** for any chatbot
2. **Types client email** in input field
3. **Clicks "Add"** button
4. **System automatically:**
   - ✅ **Existing Client**: Assigns chatbot immediately 
   - ✅ **New Email**: Creates client account + sends welcome email with temporary password
   - ✅ **Invalid Email**: Shows validation error
   - ✅ **Already Assigned**: Shows appropriate message

### **Client Experience:**
1. **Receives welcome email** with login credentials
2. **Logs in** with email + temporary password
3. **Sees simplified dashboard** with only assigned chatbots
4. **Can immediately start chatting** with assigned chatbots

### **Security Features:**
- Email validation before assignment
- Temporary passwords for new clients
- Welcome emails with login instructions
- Automatic account creation only for valid email formats
- No duplicate assignments allowed

## Implementation Sequence

### Phase 1: Database Foundation (Day 1)
1. **Update db_service.py**
   - Add 'Client' to User_Auth_Table role choices (keep existing User, Super User)
   - Create ChatbotClientMapper collection
   - Add database service functions
   - Test database operations

### Phase 2: Backend API (Day 2)
1. **Update api_models.py**
   - Add 'Client' to UserRole enum (keep existing User, Super User)
   - Add new email-based request/response models
2. **Update main.py**
   - Add email-based assignment endpoint with auto-client creation (Users and Super Users)
   - Add helper functions (password generation, email sending)
   - Update existing endpoints with three-role access control
   - Add access validation helper functions (Super Users have full access)
3. **Test API endpoints with email workflow and three-role system**

### Phase 3: Frontend Core (Day 3)
1. **Update stores and types**
   - Update UserAuthStore interface (support all three roles)
   - Update ProtectedRoute component for three-role system
2. **Create ClientDashboard**
   - Simple interface for clients
   - Chatbot selection and chat interface
3. **Update api.ts**
   - Add new client API functions

### Phase 4: Client Management UI (Day 4)
1. **Create AssignClientsModalComponent**
   - Email input interface with validation
   - Real-time client assignment/removal
   - Auto-client creation feedback
2. **Update SidebarComponent**
   - Add client assignment option for Users and Super Users
3. **Update ManageChatbotsModalComponent**
   - Add "Manage Clients" button for Users and Super Users
4. **Update App.tsx**
   - Three-role routing (Client → ClientDashboard, User/Super User → MainPage)

### Phase 5: Testing & Refinement (Day 5)
1. **End-to-end testing**
   - Test email-based assignment workflow
   - Test auto-client creation
   - Test welcome email delivery
   - Test client access restrictions
2. **UI/UX improvements**
   - Polish client dashboard
   - Improve email assignment interface
   - Test email validation and error handling
3. **Security testing**
   - Verify access controls
   - Test email validation edge cases
   - Test temporary password security

## Validation Checklist

### Database Level
- [ ] Client role added to User_Auth_Table
- [ ] ChatbotClientMapper collection created with proper indexes
- [ ] Database functions work correctly
- [ ] Unique constraints prevent duplicate assignments

### API Level
- [ ] New endpoints return correct responses
- [ ] Role-based access control works (User vs Client)
- [ ] Clients cannot access User-only endpoints
- [ ] Users cannot access Client-only endpoints
- [ ] Error handling is comprehensive

### Frontend Level
- [ ] Client dashboard shows only assigned chatbots
- [ ] Assignment modal works for Users and Super Users
- [ ] Role-based UI elements display correctly
- [ ] Navigation works for all three roles (User, Super User, Client)
- [ ] Clients cannot access User/Super User management features
- [ ] Super Users have full system access

### Security
- [ ] Clients cannot access unassigned chatbots
- [ ] Conversation isolation works correctly
- [ ] API endpoints validate user permissions
- [ ] No data leakage between users

### User Experience
- [ ] Email-based assignment is intuitive
- [ ] Auto-client creation works seamlessly
- [ ] Welcome emails are delivered correctly  
- [ ] Client dashboard is simple and effective
- [ ] Error messages are helpful
- [ ] Performance is acceptable

## Summary

This updated plan implements an **email-first assignment system** that makes client management much more user-friendly:

**Key Improvements:**
- ✅ **Simple email input** instead of complex client selection
- ✅ **Automatic client creation** for new email addresses
- ✅ **Welcome emails** with login credentials
- ✅ **Real-time assignment management** with immediate feedback
- ✅ **Intuitive UI** with email validation and error handling

**Benefits:**
- **Users and Super Users** can assign chatbots by simply typing emails (no need to know who's in the system)
- **Super Users** have full access to all chatbots and can manage any client assignments
- **New clients** are automatically onboarded with welcome emails
- **Existing clients** are assigned immediately
- **Security** is maintained with email validation and temporary passwords

This approach ensures a smooth, professional workflow where Users and Super Users can easily share chatbots with clients through a simple email interface, while maintaining the existing Super User privileges.
