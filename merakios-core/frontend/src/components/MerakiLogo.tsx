const MerakiLogo = ({ className = "" }: { className?: string }) => {
  return (
    <svg
      viewBox="0 0 200 200"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <defs>
        <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="hsl(191 100% 50%)" />
          <stop offset="50%" stopColor="hsl(217 82% 50%)" />
          <stop offset="100%" stopColor="hsl(250 100% 65%)" />
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>
      
      {/* Outer hexagon with nodes */}
      <g filter="url(#glow)">
        {/* Main hexagon shape */}
        <polygon
          points="100,20 165,55 165,125 100,160 35,125 35,55"
          fill="none"
          stroke="url(#logoGradient)"
          strokeWidth="3"
        />
        
        {/* Corner nodes */}
        <circle cx="100" cy="20" r="6" fill="url(#logoGradient)" className="animate-node-pulse" />
        <circle cx="165" cy="55" r="6" fill="url(#logoGradient)" className="animate-node-pulse" style={{ animationDelay: "0.2s" }} />
        <circle cx="165" cy="125" r="6" fill="url(#logoGradient)" className="animate-node-pulse" style={{ animationDelay: "0.4s" }} />
        <circle cx="100" cy="160" r="6" fill="url(#logoGradient)" className="animate-node-pulse" style={{ animationDelay: "0.6s" }} />
        <circle cx="35" cy="125" r="6" fill="url(#logoGradient)" className="animate-node-pulse" style={{ animationDelay: "0.8s" }} />
        <circle cx="35" cy="55" r="6" fill="url(#logoGradient)" className="animate-node-pulse" style={{ animationDelay: "1s" }} />
        
        {/* Inner hexagon */}
        <polygon
          points="100,50 135,70 135,110 100,130 65,110 65,70"
          fill="none"
          stroke="url(#logoGradient)"
          strokeWidth="2.5"
        />
        
        {/* M letter stylized */}
        <path
          d="M75,105 L75,75 L100,90 L125,75 L125,105"
          fill="none"
          stroke="url(#logoGradient)"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </g>
    </svg>
  );
};

export default MerakiLogo;
