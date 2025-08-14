import { useState } from "react";
import CreateBotUserModalComponent from "./CreateBotUserModalComponent";
import CreateBotSuperUserModalComponent from "./CreateBotSuperUserModalComponent";
import UserAuthStore from "../stores/UserAuthStore";
import ManageChatbotsModalComponent from "./ManageChatbotsModalComponent";

const WelcomeScreenComponent = () => {
    const user = UserAuthStore((state: any) => state.user);
    const [createBotModalOpen, setCreateBotModalOpen] = useState(false);
    const [existingChatbotsModalOpen, setExistingChatbotsModalOpen] = useState(false);

    const handleExistingChatbotsClick = () => {
        // Open the existing chatbots modal
        setExistingChatbotsModalOpen(true);
    }

    return (
        <div className="flex flex-col w-full flex-1 min-h-0 overflow-y-auto items-center justify-start pt-8 px-5 pb-8 relative">
            {/* Animated background elements */}
            <div className="floating-element w-24 h-24 top-20 left-20" style={{ animationDelay: '0s' }}></div>
            <div className="floating-element w-16 h-16 top-1/3 right-16" style={{ animationDelay: '3s' }}></div>
            <div className="floating-element w-20 h-20 bottom-32 left-1/4" style={{ animationDelay: '1.5s' }}></div>
            <div className="glow-element w-48 h-48 top-1/4 right-1/3" style={{ animationDelay: '2s' }}></div>
            <div className="glow-element w-32 h-32 bottom-1/4 left-1/2" style={{ animationDelay: '4s' }}></div>

            <div className="flex flex-col gap-8 lg:gap-12 w-full max-w-4xl relative z-10">
                {/* Header Section */}
                <div className="text-center space-y-6">
                    <h1 className="text-4xl sm:text-6xl font-light glass-text mb-4 leading-tight">
                        Create your personal
                        <span className="block bg-gradient-to-r from-white via-blue-200 to-purple-200 bg-clip-text text-transparent font-medium">
                            AI Chatbot
                        </span>
                    </h1>
                    <p className="text-lg glass-text opacity-80 max-w-2xl mx-auto">
                        Build intelligent conversations with your own data. Get started by creating a new chatbot or loading an existing one.
                    </p>
                </div>

                {/* Action Cards */}
                <div className="flex flex-col sm:flex-row gap-6 justify-center items-stretch">
                    <div className="glass-card p-8 flex-1 max-w-sm mx-auto group cursor-pointer"
                        onClick={() => setCreateBotModalOpen(true)}>
                        <div className="text-center space-y-4">
                            <div className="w-16 h-16 mx-auto glass rounded-full flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                                <span className="material-symbols-outlined text-3xl glass-text">
                                    robot_2
                                </span>
                            </div>
                            <h3 className="text-xl font-medium glass-text">Create New Chatbot</h3>
                            <p className="text-sm glass-text opacity-70 leading-relaxed">
                                Start fresh with a new intelligent assistant. Upload your documents and train your AI.
                            </p>
                            <div className="flex items-center justify-center space-x-2 glass-text opacity-60 text-sm">
                                <span>Get started</span>
                                <span className="material-symbols-outlined text-sm">
                                    arrow_forward
                                </span>
                            </div>
                        </div>
                    </div>

                    <div className="glass-card p-8 flex-1 max-w-sm mx-auto group cursor-pointer"
                        onClick={handleExistingChatbotsClick}>
                        <div className="text-center space-y-4">
                            <div className="w-16 h-16 mx-auto glass rounded-full flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                                <span className="material-symbols-outlined text-3xl glass-text">
                                    chat
                                </span>
                            </div>
                            <h3 className="text-xl font-medium glass-text">Load Existing Chatbot</h3>
                            <p className="text-sm glass-text opacity-70 leading-relaxed">
                                Continue where you left off. Access your previously created chatbots and their conversations.
                            </p>
                            <div className="flex items-center justify-center space-x-2 glass-text opacity-60 text-sm">
                                <span>Browse chatbots</span>
                                <span className="material-symbols-outlined text-sm">
                                    arrow_forward
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Features Section */}
                <div className="glass p-6 rounded-2xl">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 text-center">
                        <div className="space-y-3">
                            <div className="w-12 h-12 mx-auto glass-dark rounded-full flex items-center justify-center">
                                <span className="material-symbols-outlined text-xl glass-text">
                                    upload_file
                                </span>
                            </div>
                            <h4 className="font-medium glass-text text-sm">Document Upload</h4>
                            <p className="text-xs glass-text opacity-70">Support for PDF, DOCX, TXT, and CSV files</p>
                        </div>
                        <div className="space-y-3">
                            <div className="w-12 h-12 mx-auto glass-dark rounded-full flex items-center justify-center">
                                <span className="material-symbols-outlined text-xl glass-text">
                                    psychology
                                </span>
                            </div>
                            <h4 className="font-medium glass-text text-sm">AI-Powered</h4>
                            <p className="text-xs glass-text opacity-70">Advanced language models for intelligent responses</p>
                        </div>
                        <div className="space-y-3">
                            <div className="w-12 h-12 mx-auto glass-dark rounded-full flex items-center justify-center">
                                <span className="material-symbols-outlined text-xl glass-text">
                                    security
                                </span>
                            </div>
                            <h4 className="font-medium glass-text text-sm">Secure & Private</h4>
                            <p className="text-xs glass-text opacity-70">Your data stays private and secure</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Show appropriate modal based on permissions (frontend convenience only) */}
            {/* Backend will still verify permissions on API calls */}
            {user?.role === 'Super User' ? (
                <CreateBotSuperUserModalComponent
                    open={createBotModalOpen}
                    onClose={() => setCreateBotModalOpen(false)}
                />
            ) : (
                <CreateBotUserModalComponent
                    open={createBotModalOpen}
                    onClose={() => setCreateBotModalOpen(false)}
                />
            )}

            <ManageChatbotsModalComponent
                open={existingChatbotsModalOpen}
                onClose={() => setExistingChatbotsModalOpen(false)}
                onSelectChatbot={() => { }}
            />
        </div>
    )
}

export default WelcomeScreenComponent;