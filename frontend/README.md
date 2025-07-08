# Genetic Disorder Detection Frontend

A modern, responsive React frontend for the AI-driven genetic disorder detection system. Built with Next.js, TypeScript, and Tailwind CSS.

## Features

- 🔐 **Authentication System** - Secure login/register with JWT tokens
- 💬 **Interactive Chat Interface** - Real-time chat with AI about genetic data
- 📁 **VCF File Upload** - Drag & drop VCF file upload with validation
- 🧬 **Genetic Analysis Dashboard** - Comprehensive analysis results and insights
- 📊 **Chat History** - View and manage previous conversations
- 🎨 **Modern UI/UX** - Beautiful, responsive design with smooth animations
- 📱 **Mobile Responsive** - Works perfectly on all device sizes
- ⚡ **Real-time Updates** - Live chat with typing indicators and notifications

## Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **HTTP Client**: Axios
- **Notifications**: React Hot Toast
- **File Upload**: React Dropzone
- **Markdown**: React Markdown

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Backend API running on `http://localhost:8000`

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ai-driven-genetic-disorder-detection/frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   # or
   yarn install
   ```

3. **Set up environment variables**
   Create a `.env.local` file in the frontend directory:
   ```env
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
   ```

4. **Start the development server**
   ```bash
   npm run dev
   # or
   yarn dev
   ```

5. **Open your browser**
   Navigate to [http://localhost:3000](http://localhost:3000)

## Project Structure

```
frontend/
├── app/                    # Next.js App Router pages
│   ├── chat/              # Chat interface
│   ├── login/             # Authentication pages
│   ├── register/          # Registration page
│   ├── analyze/           # Direct VCF analysis
│   ├── history/           # Chat history
│   ├── settings/          # User settings
│   ├── globals.css        # Global styles
│   ├── layout.tsx         # Root layout
│   └── page.tsx           # Dashboard
├── components/            # Reusable components
│   ├── ui/               # Base UI components
│   └── FileUpload.tsx    # File upload component
├── lib/                  # Utility libraries
│   ├── api.ts           # API client
│   └── utils.ts         # Helper functions
├── types/               # TypeScript type definitions
│   └── api.ts          # API types
├── public/              # Static assets
└── package.json         # Dependencies and scripts
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking

## API Integration

The frontend communicates with the backend API through the `api.ts` client. Key endpoints:

- **Authentication**: `/auth/login`, `/auth/register`
- **Chat**: `/chat` (multipart form data)
- **Analysis**: `/analyze` (VCF file upload)
- **Chat Management**: `/chats`, `/chats/{id}`
- **Health Check**: `/health`

## Features in Detail

### Authentication
- JWT token-based authentication
- Automatic token refresh
- Protected routes
- Persistent login state

### Chat Interface
- Real-time message exchange
- File upload integration
- Message history
- Typing indicators
- Auto-scroll to latest messages

### File Upload
- Drag & drop VCF files
- File validation (.vcf, .vcf.gz)
- Size limits (100MB)
- Progress indicators
- Error handling

### Dashboard
- Overview of analysis statistics
- Quick access to features
- Recent activity
- Getting started guide

## Styling

The application uses Tailwind CSS with custom design tokens:

- **Primary Colors**: Blue theme for main actions
- **Genetic Colors**: Green theme for genetic-related elements
- **Danger Colors**: Red theme for errors and warnings
- **Custom Animations**: Smooth transitions and loading states

## Responsive Design

The frontend is fully responsive with breakpoints:
- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Development

### Code Style
- ESLint configuration for code quality
- Prettier for code formatting
- TypeScript strict mode enabled

### Component Guidelines
- Use TypeScript interfaces for props
- Implement proper error boundaries
- Follow accessibility guidelines
- Use semantic HTML elements

### State Management
- React hooks for local state
- Context API for global state (if needed)
- Proper cleanup in useEffect

## Deployment

### Build for Production
```bash
npm run build
```

### Environment Variables for Production
```env
NEXT_PUBLIC_API_BASE_URL=https://your-api-domain.com
```

### Deployment Platforms
- Vercel (recommended)
- Netlify
- AWS Amplify
- Docker

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the API documentation

## Roadmap

- [ ] Real-time notifications
- [ ] Advanced filtering and search
- [ ] Export functionality
- [ ] Dark mode theme
- [ ] Offline support
- [ ] Progressive Web App (PWA)
- [ ] Multi-language support 