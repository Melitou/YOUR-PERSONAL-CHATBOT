const WelcomeScreenComponent = () => {
    return (
        <div className="flex flex-col w-full h-full text-white items-center justify-center">
            <div className="flex flex-col gap-10 w-full">
                <h1 className="text-5xl font-extralight mt-5 text-center text-2xl sm:text-5xl text-black">
                        Create your personal AI Chatbot
                </h1>
                {/*Basic options choices*/}
                <div className="flex flex-row gap-5 w-full justify-center items-center">
                    <div className="flex flex-row w-50 gap-2 bg-[#efefef] rounded-lg shadow-md border border-gray-200 hover:shadow-lg hover:scale-105 transition-all duration-200">
                        <button className="p-3 w-full  rounded-md hover:bg-[#d5d5d5] transition-colors flex flex-col items-start justify-start text-left gap-2 text-black text-xs sm:text-sm">
                            <span className="material-symbols-outlined">
                                robot_2
                            </span>
                            Start by creating a new chatbot
                        </button>
                    </div>
                    <div className="flex flex-row w-50 gap-2 bg-[#efefef] rounded-lg shadow-md border border-gray-200 hover:shadow-lg hover:scale-105 transition-all duration-200">
                        <button className="p-3 w-full  rounded-md hover:bg-[#d5d5d5] transition-colors flex flex-col items-start justify-start text-left gap-2 text-black text-xs sm:text-sm">
                            <span className="material-symbols-outlined">
                                help
                            </span>
                            See technical guides of what you can achieve here
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default WelcomeScreenComponent;