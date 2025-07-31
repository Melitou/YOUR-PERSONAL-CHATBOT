import { useState } from "react";
import CreateBotUserModalComponent from "./CreateBotUserModalComponent";
import CreateBotSuperUserModalComponent from "./CreateBotSuperUserModalComponent";
import UserAuthStore from "../stores/UserAuthStore";

const WelcomeScreenComponent = () => {
    const user = UserAuthStore((state: any) => state.user);
    const [createBotModalOpen, setCreateBotModalOpen] = useState(false);
    
    return (
        <div className="flex flex-col w-full h-full text-white items-center justify-center">
            <div className="flex flex-col gap-10 w-full">
                <h1 className="text-5xl font-extralight mt-5 text-center text-2xl sm:text-5xl text-black">
                        Create your personal AI Chatbot
                </h1>
                {/*Basic options choices*/}
                <div className="flex flex-row gap-5 w-full justify-center items-center">
                    <div className="flex flex-row w-50 h-30 gap-2 bg-[#efefef] rounded-lg shadow-md border border-gray-200 hover:shadow-lg hover:scale-105 transition-all duration-200">
                        <button 
                        onClick={() => setCreateBotModalOpen(true)}
                        className="p-3 w-full  rounded-md hover:bg-[#d5d5d5] transition-colors flex flex-col items-start justify-start text-left gap-2 text-black text-xs sm:text-sm">
                            <span className="material-symbols-outlined">
                                robot_2
                            </span>
                            Start by creating a new chatbot
                        </button>
                    </div>
                    <div className="flex flex-row w-50 h-30 gap-2 bg-[#efefef] rounded-lg shadow-md border border-gray-200 hover:shadow-lg hover:scale-105 transition-all duration-200">
                        <button className="p-3 w-full  rounded-md hover:bg-[#d5d5d5] transition-colors flex flex-col items-start justify-start text-left gap-2 text-black text-xs sm:text-sm">
                            <span className="material-symbols-outlined">
                                chat
                            </span>
                            Load an existing chatbot
                        </button>
                    </div>
                </div>
            </div>
            
            {/* Show appropriate modal based on permissions (frontend convenience only) */}
            {/* Backend will still verify permissions on API calls */}
            {user?.role === 'Super User' ? (
                <CreateBotSuperUserModalComponent 
                    open={createBotModalOpen} 
                    onClose={() => setCreateBotModalOpen(false)} 
                    onSubmit={() => {}}
                />
            ) : (
                <CreateBotUserModalComponent 
                    open={createBotModalOpen} 
                    onClose={() => setCreateBotModalOpen(false)} 
                    onSubmit={() => {}}
                />
            )}
        </div>
    )
}

export default WelcomeScreenComponent;